"""Finance domain: Taxes, manual Payments and analytic accounting (cost centers).

Note: there is **no payment gateway integration**. The Payment model only
records the fact that a payment happened by external means (cash, transfer
or other). The system never charges a customer.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from simple_history.models import HistoricalRecords

from apps.core.models import TenantAwareModel


class TaxType(models.TextChoices):
    PERCENT = 'PERCENT', 'Porcentaje'
    FIXED = 'FIXED', 'Valor fijo'


class Tax(TenantAwareModel):
    """Configurable tax rates per tenant. Applied to reservation lines."""

    name = models.CharField(max_length=80)
    value = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='If type=PERCENT, this is a fraction (0.19 = 19%). '
        'If type=FIXED, this is a flat amount in the tenant currency.',
    )
    type = models.CharField(
        max_length=10, choices=TaxType.choices, default=TaxType.PERCENT.value
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='tenant_unique_tax_name'
            ),
        ]

    def __str__(self) -> str:
        suffix = '%' if self.type == TaxType.PERCENT.value else ''
        return f'{self.name} ({self.value}{suffix})'

    def apply_to(self, base: Decimal) -> Decimal:
        if self.type == TaxType.PERCENT.value:
            return (base * self.value).quantize(Decimal('0.01'))
        return self.value.quantize(Decimal('0.01'))


class AnalyticAccount(TenantAwareModel):
    """Cost center, typically one per Property.

    Sum of its AnalyticLines == net P&L for that property.
    """

    name = models.CharField(max_length=160)
    property = models.OneToOneField(
        'inventory.Property',
        on_delete=models.SET_NULL,
        related_name='cost_center',
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'],
                name='tenant_unique_analytic_account_name',
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def get_balance(self) -> Decimal:
        result = self.lines.aggregate(total=models.Sum('amount'))
        return (result['total'] or Decimal('0')).quantize(Decimal('0.01'))


class AnalyticLineCategory(models.TextChoices):
    INCOME = 'INCOME', 'Ingreso por alquiler'
    CLEANING_COST = 'CLEANING_COST', 'Costo de limpieza'
    MAINTENANCE = 'MAINTENANCE', 'Mantenimiento / reparación'
    UTILITIES = 'UTILITIES', 'Servicios públicos'
    COMMISSION = 'COMMISSION', 'Comisión a intermediarios'
    OTHER_EXPENSE = 'OTHER_EXPENSE', 'Otro gasto'
    OTHER_INCOME = 'OTHER_INCOME', 'Otro ingreso'


EXPENSE_CATEGORIES = {
    AnalyticLineCategory.CLEANING_COST.value,
    AnalyticLineCategory.MAINTENANCE.value,
    AnalyticLineCategory.UTILITIES.value,
    AnalyticLineCategory.COMMISSION.value,
    AnalyticLineCategory.OTHER_EXPENSE.value,
}


class AnalyticLine(TenantAwareModel):
    """One entry on the analytic ledger.

    Positive amount = income, negative = expense. Convention: anything in
    EXPENSE_CATEGORIES is normalised to negative; anything in income
    categories is normalised to positive.
    """

    account = models.ForeignKey(
        AnalyticAccount, on_delete=models.CASCADE, related_name='lines'
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    category = models.CharField(
        max_length=20,
        choices=AnalyticLineCategory.choices,
        default=AnalyticLineCategory.INCOME.value,
    )
    description = models.CharField(max_length=240, blank=True)
    # Optional generic backref so we can trace back to the source object
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    created_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['account', '-date']),
            models.Index(fields=['tenant', 'category', '-date']),
        ]

    def __str__(self) -> str:
        return f'{self.date} {self.amount} ({self.category})'

    def save(self, *args, **kwargs):
        if self.category in EXPENSE_CATEGORIES and self.amount > 0:
            self.amount = -self.amount
        elif (
            self.category not in EXPENSE_CATEGORIES
            and self.amount < 0
        ):
            self.amount = abs(self.amount)
        return super().save(*args, **kwargs)


# NOTE: Payment is split into a second migration because it FKs to
# booking.Reservation, and Reservation needs to reference finance.Tax via
# ReservationLine. Splitting avoids circular migration deps.


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Efectivo'
    TRANSFER = 'TRANSFER', 'Transferencia bancaria'
    OTHER = 'OTHER', 'Otro (especificar en notas)'


class PaymentType(models.TextChoices):
    ADVANCE = 'ADVANCE', 'Anticipo (alojamiento)'
    BALANCE = 'BALANCE', 'Pago de saldo (alojamiento)'
    EXTRA = 'EXTRA', 'Pago extra (daños / servicios adicionales)'
    REFUND = 'REFUND', 'Reembolso'


# Payment types that count toward paying down the lodging balance.
# EXTRA payments are tracked separately and never reduce balance_due.
LODGING_PAYMENT_TYPES = {PaymentType.ADVANCE.value, PaymentType.BALANCE.value}


class Payment(TenantAwareModel):
    """Manual record of money received (or refunded) for a reservation.

    NEVER charges anyone. The payment happened externally (Whatsapp,
    bank transfer, cash) and the operator records it here.
    """

    reservation = models.ForeignKey(
        'booking.Reservation', on_delete=models.PROTECT, related_name='payments'
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    type = models.CharField(
        max_length=10, choices=PaymentType.choices, default=PaymentType.ADVANCE.value
    )
    method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH.value
    )
    reference = models.CharField(
        max_length=120,
        blank=True,
        help_text='Optional external reference: bank confirmation #, '
        'voucher number, deposit slip ID, etc.',
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['reservation', '-date']),
        ]

    def __str__(self) -> str:
        return f'{self.amount} via {self.method} on {self.date}'
