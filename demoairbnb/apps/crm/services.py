"""CRM helpers: aggregate stats per contact."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.booking.models import Reservation, ReservationStatus
from apps.finance.models import LODGING_PAYMENT_TYPES, Payment, PaymentType


def get_contact_stats(contact) -> dict:
    """Return aggregated lifetime stats for a single guest contact."""
    reservations = Reservation.all_objects.filter(
        tenant_id=contact.tenant_id, guest=contact
    )

    confirmed_statuses = (
        ReservationStatus.CONFIRMED,
        ReservationStatus.CHECKED_IN,
        ReservationStatus.CHECKED_OUT,
    )
    confirmed_qs = reservations.filter(status__in=confirmed_statuses)
    cancelled_qs = reservations.filter(status=ReservationStatus.CANCELLED)

    total_billed = (
        confirmed_qs.aggregate(total=Sum('total_amount'))['total']
        or Decimal('0')
    )
    nights_total = (
        confirmed_qs.aggregate(total=Sum('nights'))['total'] or 0
    )

    payments = Payment.all_objects.filter(
        tenant_id=contact.tenant_id, reservation__guest=contact
    )
    total_lodging = (
        payments.filter(type__in=LODGING_PAYMENT_TYPES).aggregate(
            total=Sum('amount')
        )['total']
        or Decimal('0')
    )
    total_extras = (
        payments.filter(type=PaymentType.EXTRA.value).aggregate(
            total=Sum('amount')
        )['total']
        or Decimal('0')
    )
    total_refunded = (
        payments.filter(type=PaymentType.REFUND.value).aggregate(
            total=Sum('amount')
        )['total']
        or Decimal('0')
    )

    outstanding = (
        total_billed - (total_lodging - total_refunded)
    ).quantize(Decimal('0.01'))

    first_check_in = (
        confirmed_qs.order_by('check_in').values_list('check_in', flat=True).first()
    )
    last_check_out = (
        confirmed_qs.order_by('-check_out').values_list('check_out', flat=True).first()
    )

    return {
        'contact_id': contact.id,
        'reservations_count': reservations.count(),
        'confirmed_reservations_count': confirmed_qs.count(),
        'cancelled_reservations_count': cancelled_qs.count(),
        'total_billed': total_billed.quantize(Decimal('0.01')),
        'total_lodging_paid': (total_lodging - total_refunded).quantize(Decimal('0.01')),
        'total_extras_paid': total_extras.quantize(Decimal('0.01')),
        'total_refunded': total_refunded.quantize(Decimal('0.01')),
        'outstanding_balance': outstanding,
        'first_check_in': first_check_in,
        'last_check_out': last_check_out,
        'nights_total': nights_total,
    }
