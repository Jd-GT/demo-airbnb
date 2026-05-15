from __future__ import annotations

import io
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.booking.models import (
    PaymentStatus,
    Reservation,
    ReservationStatus,
)

from .models import (
    LODGING_PAYMENT_TYPES,
    AnalyticAccount,
    AnalyticLine,
    AnalyticLineCategory,
    Payment,
    PaymentType,
)

ACTIVE_REVENUE_STATUSES = (
    ReservationStatus.DRAFT,
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
    ReservationStatus.CHECKED_OUT,
)
MONTH_LABELS = [
    'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
    'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]


def resolve_year_month(query_params) -> tuple[int, int]:
    today = timezone.now().date()
    year_raw = query_params.get('year', today.year)
    month_raw = query_params.get('month', today.month)

    try:
        year = int(year_raw)
        month = int(month_raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'detail': 'year and month must be integers.'}) from exc

    if year < 2000 or year > 2100:
        raise ValidationError({'year': 'year must be between 2000 and 2100.'})
    if month < 1 or month > 12:
        raise ValidationError({'month': 'month must be between 1 and 12.'})
    return year, month


def get_month_window(year: int, month: int) -> tuple[date, date, int]:
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    return start_date, end_date, monthrange(year, month)[1]


def overlap_nights_for_period(
    check_in: date, check_out: date, period_start: date, period_end: date
) -> int:
    start = max(check_in, period_start)
    end = min(check_out, period_end)
    if start >= end:
        return 0
    return (end - start).days


def get_property_month_metrics(
    property_obj, *, year: int, month: int
) -> dict[str, Decimal | float]:
    month_start, month_end, days_in_month = get_month_window(year, month)
    reservations = Reservation.all_objects.filter(
        tenant_id=property_obj.tenant_id,
        property=property_obj,
        status__in=ACTIVE_REVENUE_STATUSES,
    )

    monthly_revenue = Decimal('0.00')
    occupied_nights = 0
    for reservation in reservations:
        if month_start <= reservation.check_in < month_end:
            monthly_revenue += reservation.total_amount
        occupied_nights += overlap_nights_for_period(
            reservation.check_in,
            reservation.check_out,
            month_start,
            month_end,
        )

    occupancy_rate = (
        round((occupied_nights / days_in_month) * 100, 2) if days_in_month else 0
    )
    adr = (
        (monthly_revenue / occupied_nights).quantize(Decimal('0.01'))
        if occupied_nights
        else Decimal('0.00')
    )
    return {
        'monthly_revenue': monthly_revenue.quantize(Decimal('0.01')),
        'occupancy_rate': occupancy_rate,
        'occupied_nights': occupied_nights,
        'days_in_month': days_in_month,
        'adr': adr,
    }


def get_finance_analytics(*, tenant_id, year: int, month: int) -> dict:
    reservations = Reservation.all_objects.filter(
        tenant_id=tenant_id,
        status__in=ACTIVE_REVENUE_STATUSES,
        check_in__year=year,
    ).select_related('property')

    monthly_totals = {month_index: Decimal('0.00') for month_index in range(1, 13)}
    property_totals: dict[tuple[str, str], Decimal] = defaultdict(
        lambda: Decimal('0.00')
    )

    for reservation in reservations:
        monthly_totals[reservation.check_in.month] += reservation.total_amount
        property_key = (str(reservation.property_id), reservation.property.name)
        property_totals[property_key] += reservation.total_amount

    revenue_by_property = [
        {
            'property_id': property_id,
            'name': name,
            'ingresos': total.quantize(Decimal('0.01')),
        }
        for (property_id, name), total in sorted(
            property_totals.items(), key=lambda item: item[0][1]
        )
    ]

    return {
        'monthly_revenue_total': monthly_totals[month].quantize(Decimal('0.01')),
        'annual_revenue_total': sum(monthly_totals.values()).quantize(Decimal('0.01')),
        'monthly_revenue_series': [
            {
                'month_index': month_index,
                'month': MONTH_LABELS[month_index - 1],
                'ingresos': monthly_totals[month_index].quantize(Decimal('0.01')),
            }
            for month_index in range(1, 13)
        ],
        'revenue_by_property': revenue_by_property,
    }


# ---------- Cost centers / Analytic Accounting ----------

def ensure_cost_center_for_property(property_obj) -> AnalyticAccount:
    """Idempotent: every Property must have its own cost center."""
    existing = AnalyticAccount.all_objects.filter(
        tenant_id=property_obj.tenant_id, property=property_obj
    ).first()
    if existing:
        return existing
    return AnalyticAccount.all_objects.create(
        tenant_id=property_obj.tenant_id,
        property=property_obj,
        name=f'Centro costo — {property_obj.name}',
    )


@transaction.atomic
def accrue_reservation_income(reservation: Reservation) -> AnalyticLine | None:
    """Create the INCOME analytic line for a confirmed reservation.

    Idempotent: if the line already exists for this reservation, returns it.
    Also creates the COMMISSION expense line if there's an agent_commission.
    """
    account = ensure_cost_center_for_property(reservation.property)

    income_line = AnalyticLine.all_objects.filter(
        tenant_id=reservation.tenant_id,
        account=account,
        reference_type='Reservation',
        reference_id=reservation.id,
        category=AnalyticLineCategory.INCOME.value,
    ).first()

    if income_line is None:
        income_line = AnalyticLine.all_objects.create(
            tenant_id=reservation.tenant_id,
            account=account,
            date=reservation.check_in,
            amount=reservation.total_amount,
            category=AnalyticLineCategory.INCOME.value,
            description=(
                f'Reserva {reservation.id} — {reservation.guest.name} '
                f'({reservation.check_in} → {reservation.check_out})'
            ),
            reference_type='Reservation',
            reference_id=reservation.id,
            created_by=reservation.created_by,
        )

    if reservation.agent_commission > 0:
        AnalyticLine.all_objects.get_or_create(
            tenant_id=reservation.tenant_id,
            account=account,
            reference_type='Reservation',
            reference_id=reservation.id,
            category=AnalyticLineCategory.COMMISSION.value,
            defaults={
                'date': reservation.check_in,
                'amount': reservation.agent_commission,
                'description': (
                    f'Comisión agente — {reservation.agent.name if reservation.agent else ""}'
                ),
                'created_by': reservation.created_by,
            },
        )

    return income_line


# ---------- Payments ----------

def _recompute_payment_status(reservation: Reservation) -> Reservation:
    """Recalc Reservation cache fields from its payments.

    `amount_paid`        = lodging inflows (ADVANCE+BALANCE) - refunds.
    `extras_received`    = sum of EXTRA-type payments (separate bucket
                           for damages, cleaning fees post check-in,
                           breakfast, services, etc.). Never reduces
                           the lodging balance owed.
    `payment_status`     = derived from amount_paid vs total_amount.
    """
    lodging_inflows = (
        reservation.payments.filter(type__in=LODGING_PAYMENT_TYPES).aggregate(
            total=models.Sum('amount')
        )['total']
        or Decimal('0')
    )
    refunds = (
        reservation.payments.filter(type=PaymentType.REFUND.value).aggregate(
            total=models.Sum('amount')
        )['total']
        or Decimal('0')
    )
    extras = (
        reservation.payments.filter(type=PaymentType.EXTRA.value).aggregate(
            total=models.Sum('amount')
        )['total']
        or Decimal('0')
    )

    net_lodging = (lodging_inflows - refunds).quantize(Decimal('0.01'))
    reservation.amount_paid = net_lodging if net_lodging >= 0 else Decimal('0')
    reservation.extras_received = extras.quantize(Decimal('0.01'))

    if reservation.amount_paid > reservation.total_amount:
        # Should be impossible given the validation in register_payment,
        # but keep the OVERPAID status as a safety net for legacy data.
        reservation.payment_status = PaymentStatus.OVERPAID.value
    elif (
        reservation.amount_paid >= reservation.total_amount
        and reservation.total_amount > 0
    ):
        reservation.payment_status = PaymentStatus.PAID.value
    elif reservation.amount_paid > 0:
        reservation.payment_status = PaymentStatus.PARTIAL.value
    else:
        reservation.payment_status = PaymentStatus.PENDING.value
    reservation.save(
        update_fields=[
            'amount_paid',
            'extras_received',
            'payment_status',
            'updated_at',
        ]
    )
    return reservation


@transaction.atomic
def register_payment(
    *,
    reservation: Reservation,
    amount: Decimal,
    method: str,
    type: str,
    date: date,
    reference: str = '',
    notes: str = '',
    recorded_by=None,
) -> Payment:
    """Record a payment manually. Validates lodging overpayment.

    Rules:
      - ADVANCE / BALANCE → counted toward `amount_paid`. Cannot push
        the lodging balance below 0 (no overpayment of lodging). If the
        guest pays extra (damages, late services, etc.) use type=EXTRA.
      - EXTRA → no upper bound. Tracked in `extras_received`.
      - REFUND → subtracts from `amount_paid`.
    """
    amount = Decimal(str(amount)).quantize(Decimal('0.01'))
    if amount <= 0:
        raise ValidationError({'amount': 'Amount must be positive.'})

    if type in LODGING_PAYMENT_TYPES:
        balance_due = (reservation.total_amount - reservation.amount_paid).quantize(
            Decimal('0.01')
        )
        if balance_due <= 0:
            raise ValidationError(
                {
                    'amount': (
                        'La reserva ya está completamente pagada. '
                        'Si el huésped paga extras (daños, servicios), '
                        'usa el tipo "Pago extra".'
                    )
                }
            )
        if amount > balance_due:
            raise ValidationError(
                {
                    'amount': (
                        f'El monto excede el saldo pendiente '
                        f'(${balance_due}). Cobra como máximo ese valor, '
                        f'o registra el sobrante como "Pago extra" en otro pago.'
                    )
                }
            )
    elif type == PaymentType.REFUND.value:
        if amount > reservation.amount_paid:
            raise ValidationError(
                {
                    'amount': (
                        f'No puedes reembolsar más de lo que se ha pagado '
                        f'(${reservation.amount_paid}).'
                    )
                }
            )

    payment = Payment.all_objects.create(
        tenant_id=reservation.tenant_id,
        reservation=reservation,
        date=date,
        amount=amount,
        type=type,
        method=method,
        reference=reference,
        notes=notes,
        recorded_by=recorded_by,
    )
    _recompute_payment_status(reservation)
    return payment


@transaction.atomic
def delete_payment(payment: Payment) -> None:
    reservation = payment.reservation
    payment.delete()
    _recompute_payment_status(reservation)


# ---------- Expenses (analytic lines manuales) ----------

@transaction.atomic
def register_expense(
    *,
    tenant_id,
    account: AnalyticAccount,
    amount: Decimal,
    category: str,
    date: date,
    description: str = '',
    recorded_by=None,
) -> AnalyticLine:
    return AnalyticLine.all_objects.create(
        tenant_id=tenant_id,
        account=account,
        date=date,
        amount=amount,
        category=category,
        description=description,
        created_by=recorded_by,
    )


# ---------- P&L ----------

def get_profit_and_loss(
    *, tenant_id, account: AnalyticAccount | None = None,
    from_date: date | None = None, to_date: date | None = None,
) -> dict:
    qs = AnalyticLine.all_objects.filter(tenant_id=tenant_id)
    if account is not None:
        qs = qs.filter(account=account)
    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)

    income = Decimal('0')
    expenses = Decimal('0')
    by_category: dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
    for line in qs:
        if line.amount >= 0:
            income += line.amount
        else:
            expenses += line.amount
        by_category[line.category] += line.amount

    net = income + expenses  # expenses already negative
    return {
        'income': income.quantize(Decimal('0.01')),
        'expenses': expenses.quantize(Decimal('0.01')),
        'net': net.quantize(Decimal('0.01')),
        'by_category': {
            k: v.quantize(Decimal('0.01')) for k, v in sorted(by_category.items())
        },
    }


# ---------- Excel export ----------

def build_pnl_xlsx(*, tenant_id, year: int) -> bytes:
    """Return an .xlsx file (bytes) with annual P&L per cost center."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        raise ValidationError(
            {'detail': 'openpyxl is not installed. pip install openpyxl'}
        )

    wb = Workbook()
    ws = wb.active
    ws.title = f'P&L {year}'

    bold = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='1F2937')
    income_fill = PatternFill('solid', fgColor='DCFCE7')
    expense_fill = PatternFill('solid', fgColor='FEE2E2')
    center = Alignment(horizontal='center')

    headers = ['Centro de costo'] + MONTH_LABELS + ['Total año']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = bold
        cell.fill = header_fill
        cell.alignment = center

    accounts = AnalyticAccount.all_objects.filter(
        tenant_id=tenant_id, is_active=True
    ).order_by('name')

    grand_total = Decimal('0')
    for account in accounts:
        row = [account.name]
        annual = Decimal('0')
        for month in range(1, 13):
            start, end, _ = get_month_window(year, month)
            month_total = (
                AnalyticLine.all_objects.filter(
                    tenant_id=tenant_id,
                    account=account,
                    date__gte=start,
                    date__lt=end,
                ).aggregate(total=models.Sum('amount'))['total']
                or Decimal('0')
            )
            annual += month_total
            row.append(float(month_total.quantize(Decimal('0.01'))))
        row.append(float(annual.quantize(Decimal('0.01'))))
        grand_total += annual
        ws.append(row)
        for idx, cell in enumerate(ws[ws.max_row], start=1):
            if idx == 1:
                continue
            value = cell.value or 0
            if value < 0:
                cell.fill = expense_fill
            elif value > 0:
                cell.fill = income_fill

    ws.append([])
    ws.append(['TOTAL', '', '', '', '', '', '', '', '', '', '', '', '', float(grand_total)])
    for cell in ws[ws.max_row]:
        cell.font = Font(bold=True)

    # Column widths
    ws.column_dimensions['A'].width = 32
    for col_letter in 'BCDEFGHIJKLMN':
        ws.column_dimensions[col_letter].width = 12

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_payments_xlsx(
    *, tenant_id, from_date: date | None = None, to_date: date | None = None
) -> bytes:
    """Listado de pagos en Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        raise ValidationError(
            {'detail': 'openpyxl is not installed. pip install openpyxl'}
        )

    wb = Workbook()
    ws = wb.active
    ws.title = 'Pagos'

    headers = [
        'Fecha', 'Reserva', 'Huésped', 'Propiedad',
        'Monto', 'Tipo', 'Categoría', 'Método', 'Referencia', 'Notas',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F2937')

    qs = Payment.all_objects.filter(tenant_id=tenant_id).select_related(
        'reservation__guest', 'reservation__property'
    )
    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)

    lodging_total = Decimal('0')
    extras_total = Decimal('0')
    refunds_total = Decimal('0')
    for payment in qs.order_by('-date'):
        if payment.type in LODGING_PAYMENT_TYPES:
            category = 'Alojamiento'
            lodging_total += payment.amount
        elif payment.type == PaymentType.EXTRA.value:
            category = 'Extra (daños/servicios)'
            extras_total += payment.amount
        elif payment.type == PaymentType.REFUND.value:
            category = 'Reembolso'
            refunds_total += payment.amount
        else:
            category = payment.type
        ws.append(
            [
                payment.date.isoformat(),
                str(payment.reservation_id),
                payment.reservation.guest.name,
                payment.reservation.property.name,
                float(payment.amount),
                payment.type,
                category,
                payment.method,
                payment.reference,
                payment.notes,
            ]
        )

    ws.append([])
    ws.append(['Alojamiento neto', '', '', '',
               float(lodging_total - refunds_total), '', '', '', '', ''])
    ws.append(['Extras', '', '', '', float(extras_total), '', '', '', '', ''])
    ws.append(['Reembolsos', '', '', '', float(refunds_total), '', '', '', '', ''])
    ws.append(['TOTAL ENTRADAS', '', '', '',
               float(lodging_total + extras_total - refunds_total),
               '', '', '', '', ''])
    for row_offset in (1, 2, 3, 4):
        for cell in ws[ws.max_row - 4 + row_offset]:
            cell.font = Font(bold=True)

    for col_letter, width in zip(
        'ABCDEFGHIJ', [12, 36, 24, 24, 12, 10, 22, 12, 18, 30]
    ):
        ws.column_dimensions[col_letter].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_occupancy_xlsx(*, tenant_id, year: int) -> bytes:
    """Occupancy & ADR per property per month."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        raise ValidationError(
            {'detail': 'openpyxl is not installed. pip install openpyxl'}
        )

    from apps.inventory.models import Property

    wb = Workbook()
    ws = wb.active
    ws.title = f'Ocupación {year}'

    headers = ['Propiedad'] + MONTH_LABELS + ['Promedio anual']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F2937')

    for prop in Property.all_objects.filter(tenant_id=tenant_id).order_by('name'):
        row = [prop.name]
        annual_occ = []
        for month in range(1, 13):
            metrics = get_property_month_metrics(prop, year=year, month=month)
            row.append(float(metrics['occupancy_rate']))
            annual_occ.append(metrics['occupancy_rate'])
        row.append(round(sum(annual_occ) / 12, 2))
        ws.append(row)

    for col_letter, width in zip('ABCDEFGHIJKLMN', [32] + [10] * 13):
        ws.column_dimensions[col_letter].width = width

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
