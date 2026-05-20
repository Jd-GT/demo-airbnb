from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from simple_history.models import HistoricalRecords

from apps.core.models import TenantAwareModel


class ReservationStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    CHECKED_IN = 'CHECKED_IN', 'Checked-in'
    CHECKED_OUT = 'CHECKED_OUT', 'Checked-out'
    CANCELLED = 'CANCELLED', 'Cancelled'


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Sin pagos'
    PARTIAL = 'PARTIAL', 'Pagado parcialmente'
    PAID = 'PAID', 'Pagado completo'
    OVERPAID = 'OVERPAID', 'Sobrepagado'


class PriceRule(TenantAwareModel):
    """Optional rule that overrides Property.base_price within a date range.

    Multiple rules may apply to the same date; the one with the highest
    `priority` wins. Within rules of the same priority, more specific
    (single-property) wins over wildcard.
    """

    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    is_percent = models.BooleanField(
        default=False,
        help_text='If True, modifier multiplies the base price '
        '(1.20 = +20%). If False, modifier replaces it as a flat '
        'nightly rate.',
    )
    modifier = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    min_nights = models.PositiveIntegerField(
        default=1, help_text='Minimum nights required when this rule applies.'
    )
    priority = models.PositiveIntegerField(
        default=10,
        help_text='Higher value wins when multiple rules overlap.',
    )
    properties = models.ManyToManyField(
        'inventory.Property',
        blank=True,
        related_name='price_rules',
        help_text='Empty = applies to ALL tenant properties.',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-priority', 'start_date']
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__gte=F('start_date')),
                name='pricerule_end_after_start',
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'is_active', 'start_date', 'end_date']),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.start_date} → {self.end_date})'


class ReservationSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    ICAL = "ical", "iCal (externo)"


class Reservation(TenantAwareModel):
    property = models.ForeignKey(
        'inventory.Property', on_delete=models.PROTECT, related_name='reservations'
    )
    guest = models.ForeignKey(
        'crm.Contact', on_delete=models.PROTECT, related_name='guest_reservations'
    )
    agent = models.ForeignKey(
        'crm.Contact',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='agent_reservations',
    )
    check_in = models.DateField()
    check_out = models.DateField()
    nights = models.PositiveIntegerField(default=1)
    subtotal_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    cleaning_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    tax_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    extras_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Sum of EXTRA-type payments (damages, extra services). '
        'Does NOT count toward the lodging balance_due.',
    )
    agent_commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    status = models.CharField(
        max_length=16,
        choices=ReservationStatus.choices,
        default=ReservationStatus.CONFIRMED,
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING.value,
    )
    source = models.CharField(
        max_length=20,
        choices=ReservationSource.choices,
        default=ReservationSource.MANUAL,
    )
    created_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ['-check_in', '-created_at']
        constraints = [
            models.CheckConstraint(
                check=Q(check_out__gt=F('check_in')),
                name='reservation_check_out_after_check_in',
            ),
        ]

    def __str__(self) -> str:
        return f'Reservation {self.id}'

    def get_balance_due(self) -> Decimal:
        return (self.total_amount - self.amount_paid).quantize(Decimal('0.01'))


class ReservationLineType(models.TextChoices):
    NIGHT = 'NIGHT', 'Cargo por noche'
    FEE = 'FEE', 'Tarifa única (limpieza, etc.)'
    EXTRA = 'EXTRA', 'Servicio adicional'
    DISCOUNT = 'DISCOUNT', 'Descuento'


class ReservationLine(TenantAwareModel):
    """Detail line on a reservation. Sum of lines = subtotal_amount."""

    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name='lines'
    )
    type = models.CharField(
        max_length=10,
        choices=ReservationLineType.choices,
        default=ReservationLineType.NIGHT.value,
    )
    description = models.CharField(max_length=240)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    taxes = models.ManyToManyField('finance.Tax', blank=True, related_name='lines')

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.description}: {self.quantity} x {self.unit_price}'

    @property
    def line_subtotal(self) -> Decimal:
        return (Decimal(self.quantity) * Decimal(self.unit_price)).quantize(
            Decimal('0.01')
        )

    def line_tax_total(self) -> Decimal:
        total = Decimal('0')
        base = self.line_subtotal
        for tax in self.taxes.all():
            total += tax.apply_to(base)
        return total.quantize(Decimal('0.01'))
