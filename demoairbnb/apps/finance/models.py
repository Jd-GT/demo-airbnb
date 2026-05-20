"""Finance domain: taxes, manual payments, analytics and reports."""

from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from apps.core.models import TenantAwareModel
from apps.inventory.models import Property


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
    """Cost center, typically one per property."""

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
    """One entry on the analytic ledger."""

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
        elif self.category not in EXPENSE_CATEGORIES and self.amount < 0:
            self.amount = abs(self.amount)
        return super().save(*args, **kwargs)


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Efectivo'
    TRANSFER = 'TRANSFER', 'Transferencia bancaria'
    OTHER = 'OTHER', 'Otro (especificar en notas)'


class PaymentType(models.TextChoices):
    ADVANCE = 'ADVANCE', 'Anticipo (alojamiento)'
    BALANCE = 'BALANCE', 'Pago de saldo (alojamiento)'
    EXTRA = 'EXTRA', 'Pago extra (daños / servicios adicionales)'
    REFUND = 'REFUND', 'Reembolso'


LODGING_PAYMENT_TYPES = {PaymentType.ADVANCE.value, PaymentType.BALANCE.value}


class Payment(TenantAwareModel):
    """Manual record of money received or refunded for a reservation."""

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


class PropertyProfitabilityReport(TenantAwareModel):
    """Profit and loss report per property for a period."""

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='profitability_reports'
    )
    year = models.IntegerField()
    month = models.IntegerField()
    gross_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commissions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cleaning_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maintenance_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    utilities_costs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    property_management_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    other_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    occupied_nights = models.IntegerField(default=0)
    total_nights = models.IntegerField(default=0)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    revenue_per_available_night = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    class Meta:
        ordering = ['-year', '-month']
        constraints = [
            models.UniqueConstraint(
                fields=['property', 'year', 'month'],
                name='unique_property_profitability_period',
            )
        ]

    def calculate_metrics(self):
        self.net_revenue = (self.gross_revenue - self.commissions).quantize(
            Decimal('0.01')
        )
        self.total_expenses = (
            self.cleaning_costs
            + self.maintenance_costs
            + self.utilities_costs
            + self.platform_fees
            + self.property_management_fee
            + self.other_expenses
        ).quantize(Decimal('0.01'))
        self.net_profit = (self.net_revenue - self.total_expenses).quantize(
            Decimal('0.01')
        )
        self.profit_margin = (
            (self.net_profit / self.net_revenue * Decimal('100')).quantize(
                Decimal('0.01')
            )
            if self.net_revenue > 0
            else Decimal('0.00')
        )
        self.occupancy_rate = (
            (Decimal(self.occupied_nights) / Decimal(self.total_nights) * Decimal('100'))
            .quantize(Decimal('0.01'))
            if self.total_nights
            else Decimal('0.00')
        )
        self.avg_daily_rate = (
            (self.gross_revenue / Decimal(self.occupied_nights)).quantize(
                Decimal('0.01')
            )
            if self.occupied_nights
            else Decimal('0.00')
        )
        self.revenue_per_available_night = (
            (self.net_revenue / Decimal(self.total_nights)).quantize(Decimal('0.01'))
            if self.total_nights
            else Decimal('0.00')
        )

    def save(self, *args, **kwargs):
        self.calculate_metrics()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.property.name} - {self.year}/{self.month:02d}'


class Voucher(TenantAwareModel):
    """Voucher or receipt for guest stays or transactions."""

    STATUS_CHOICES = [
        ('issued', 'Emitido'),
        ('sent', 'Enviado'),
        ('downloaded', 'Descargado'),
        ('voided', 'Anulado'),
    ]

    reference_number = models.CharField(max_length=50, unique=True)
    voucher_type = models.CharField(
        max_length=20,
        choices=[
            ('stay', 'Comprobante de Estadía'),
            ('payment', 'Recibo de Pago'),
            ('invoice', 'Factura'),
        ],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
    guest_name = models.CharField(max_length=160)
    guest_email = models.EmailField()
    property_name = models.CharField(max_length=160)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    issue_date = models.DateField(auto_now_add=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    pdf_file = models.FileField(upload_to='vouchers/%Y/%m/', null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self) -> str:
        return f'{self.reference_number} - {self.guest_name}'
