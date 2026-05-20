from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.booking.models import Reservation, ReservationStatus
from .models import PropertyProfitabilityReport, Voucher


ACTIVE_REVENUE_STATUSES = (
    ReservationStatus.DRAFT,
    ReservationStatus.CONFIRMED,
)
MONTH_LABELS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def resolve_year_month(query_params) -> tuple[int, int]:
    today = timezone.now().date()
    year_raw = query_params.get("year", today.year)
    month_raw = query_params.get("month", today.month)

    try:
        year = int(year_raw)
        month = int(month_raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"detail": "year and month must be integers."}) from exc

    if year < 2000 or year > 2100:
        raise ValidationError({"year": "year must be between 2000 and 2100."})
    if month < 1 or month > 12:
        raise ValidationError({"month": "month must be between 1 and 12."})
    return year, month


def get_month_window(year: int, month: int) -> tuple[date, date, int]:
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    return start_date, end_date, monthrange(year, month)[1]


def overlap_nights_for_period(check_in: date, check_out: date, period_start: date, period_end: date) -> int:
    start = max(check_in, period_start)
    end = min(check_out, period_end)
    if start >= end:
        return 0
    return (end - start).days


def get_property_month_metrics(property_obj, *, year: int, month: int) -> dict[str, Decimal | float]:
    month_start, month_end, days_in_month = get_month_window(year, month)
    reservations = Reservation.all_objects.filter(
        tenant_id=property_obj.tenant_id,
        property=property_obj,
        status__in=ACTIVE_REVENUE_STATUSES,
    )

    monthly_revenue = Decimal("0.00")
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

    occupancy_rate = round((occupied_nights / days_in_month) * 100, 2) if days_in_month else 0
    return {
        "monthly_revenue": monthly_revenue.quantize(Decimal("0.01")),
        "occupancy_rate": occupancy_rate,
    }


def get_finance_analytics(*, tenant_id, year: int, month: int) -> dict:
    reservations = Reservation.all_objects.filter(
        tenant_id=tenant_id,
        status__in=ACTIVE_REVENUE_STATUSES,
        check_in__year=year,
    ).select_related("property")

    monthly_totals = {month_index: Decimal("0.00") for month_index in range(1, 13)}
    property_totals: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0.00"))

    for reservation in reservations:
        monthly_totals[reservation.check_in.month] += reservation.total_amount
        property_key = (str(reservation.property_id), reservation.property.name)
        property_totals[property_key] += reservation.total_amount

    revenue_by_property = [
        {
            "property_id": property_id,
            "name": name,
            "ingresos": total.quantize(Decimal("0.01")),
        }
        for (property_id, name), total in sorted(property_totals.items(), key=lambda item: item[0][1])
    ]

    return {
        "monthly_revenue_total": monthly_totals[month].quantize(Decimal("0.01")),
        "annual_revenue_total": sum(monthly_totals.values()).quantize(Decimal("0.01")),
        "monthly_revenue_series": [
            {
                "month_index": month_index,
                "month": MONTH_LABELS[month_index - 1],
                "ingresos": monthly_totals[month_index].quantize(Decimal("0.01")),
            }
            for month_index in range(1, 13)
        ],
        "revenue_by_property": revenue_by_property,
    }


def calculate_property_profitability(
    property_obj, *, year: int, month: int, **expenses
) -> PropertyProfitabilityReport:
    """Calculate and create P&L report for a property."""
    month_start, month_end, days_in_month = get_month_window(year, month)
    reservations = Reservation.all_objects.filter(
        tenant_id=property_obj.tenant_id,
        property=property_obj,
        status__in=ACTIVE_REVENUE_STATUSES,
    )

    # Calculate revenue
    gross_revenue = Decimal("0.00")
    occupied_nights = 0

    for reservation in reservations:
        if month_start <= reservation.check_in < month_end:
            gross_revenue += reservation.total_amount
        occupied_nights += overlap_nights_for_period(
            reservation.check_in,
            reservation.check_out,
            month_start,
            month_end,
        )

    # Process expenses
    commissions = Decimal(str(expenses.get("commissions", 0)))
    cleaning_costs = Decimal(str(expenses.get("cleaning_costs", 0)))
    maintenance_costs = Decimal(str(expenses.get("maintenance_costs", 0)))
    utilities_costs = Decimal(str(expenses.get("utilities_costs", 0)))
    platform_fees = Decimal(str(expenses.get("platform_fees", 0)))
    property_management_fee = Decimal(str(expenses.get("property_management_fee", 0)))
    other_expenses = Decimal(str(expenses.get("other_expenses", 0)))

    # Calculate metrics
    net_revenue = gross_revenue - commissions
    total_expenses = (
        cleaning_costs
        + maintenance_costs
        + utilities_costs
        + platform_fees
        + property_management_fee
        + other_expenses
    )
    net_profit = net_revenue - total_expenses

    profit_margin = (
        (net_profit / net_revenue * 100).quantize(Decimal("0.01"))
        if net_revenue > 0
        else Decimal("0.00")
    )

    occupancy_rate = (
        (Decimal(occupied_nights) / Decimal(days_in_month) * 100).quantize(Decimal("0.01"))
        if days_in_month
        else Decimal("0.00")
    )
    avg_daily_rate = (
        (gross_revenue / Decimal(occupied_nights)).quantize(Decimal("0.01"))
        if occupied_nights > 0
        else Decimal("0.00")
    )
    revenue_per_available_night = (
        (net_revenue / Decimal(days_in_month)).quantize(Decimal("0.01"))
        if days_in_month
        else Decimal("0.00")
    )

    # Create or update report
    report, _ = PropertyProfitabilityReport.all_objects.update_or_create(
        tenant_id=property_obj.tenant_id,
        property=property_obj,
        year=year,
        month=month,
        defaults={
            "gross_revenue": gross_revenue.quantize(Decimal("0.01")),
            "commissions": commissions.quantize(Decimal("0.01")),
            "net_revenue": net_revenue.quantize(Decimal("0.01")),
            "cleaning_costs": cleaning_costs.quantize(Decimal("0.01")),
            "maintenance_costs": maintenance_costs.quantize(Decimal("0.01")),
            "utilities_costs": utilities_costs.quantize(Decimal("0.01")),
            "platform_fees": platform_fees.quantize(Decimal("0.01")),
            "property_management_fee": property_management_fee.quantize(Decimal("0.01")),
            "other_expenses": other_expenses.quantize(Decimal("0.01")),
            "total_expenses": total_expenses.quantize(Decimal("0.01")),
            "net_profit": net_profit.quantize(Decimal("0.01")),
            "profit_margin": profit_margin,
            "occupied_nights": occupied_nights,
            "total_nights": days_in_month,
            "occupancy_rate": occupancy_rate,
            "avg_daily_rate": avg_daily_rate,
            "revenue_per_available_night": revenue_per_available_night,
        },
    )
    return report


def generate_reference_number(voucher_type: str) -> str:
    """Generate unique voucher reference number."""
    prefix_map = {"stay": "EST", "payment": "PAG", "invoice": "FAC"}
    prefix = prefix_map.get(voucher_type, "VOC")
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    unique_part = str(uuid4())[:8].upper()
    return f"{prefix}-{timestamp}-{unique_part}"


def create_voucher(
    tenant_id,
    *,
    voucher_type: str,
    guest_name: str,
    guest_email: str,
    property_name: str,
    gross_amount: Decimal,
    tax_amount: Decimal = Decimal("0.00"),
    check_in: date | None = None,
    check_out: date | None = None,
    notes: str = "",
) -> Voucher:
    """Create a new voucher."""
    reference_number = generate_reference_number(voucher_type)
    net_amount = gross_amount - tax_amount

    voucher = Voucher.objects.create(
        tenant_id=tenant_id,
        reference_number=reference_number,
        voucher_type=voucher_type,
        guest_name=guest_name,
        guest_email=guest_email,
        property_name=property_name,
        gross_amount=gross_amount,
        tax_amount=tax_amount,
        net_amount=net_amount,
        check_in=check_in,
        check_out=check_out,
        notes=notes,
    )
    return voucher

