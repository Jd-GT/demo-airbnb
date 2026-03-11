from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from apps.crm.models import ContactType
from apps.inventory.models import Property

from .models import Reservation, ReservationStatus


ACTIVE_BLOCKING_STATUSES = (ReservationStatus.DRAFT, ReservationStatus.CONFIRMED)


@dataclass(frozen=True)
class QuoteBreakdown:
    nights: int
    nightly_rate: Decimal
    subtotal_amount: Decimal
    cleaning_fee: Decimal
    total_amount: Decimal


def _nights_between(check_in: date, check_out: date) -> int:
    nights = (check_out - check_in).days
    if nights <= 0:
        raise serializers.ValidationError({"check_out": "check_out must be after check_in."})
    return nights


def calculate_quote(*, property_obj: Property, check_in: date, check_out: date) -> QuoteBreakdown:
    nights = _nights_between(check_in, check_out)
    subtotal = nights * property_obj.base_price
    total = subtotal + property_obj.cleaning_fee
    return QuoteBreakdown(
        nights=nights,
        nightly_rate=property_obj.base_price,
        subtotal_amount=subtotal,
        cleaning_fee=property_obj.cleaning_fee,
        total_amount=total,
    )


def check_availability(*, tenant_id, property_id, check_in: date, check_out: date, exclude_reservation_id=None) -> tuple[bool, list[str]]:
    _nights_between(check_in, check_out)

    overlaps = Q(check_in__lt=check_out) & Q(check_out__gt=check_in)
    query = Reservation.all_objects.filter(
        tenant_id=tenant_id,
        property_id=property_id,
        status__in=ACTIVE_BLOCKING_STATUSES,
    ).filter(overlaps)
    if exclude_reservation_id:
        query = query.exclude(id=exclude_reservation_id)

    conflicts = list(query.values_list("id", flat=True))
    return len(conflicts) == 0, [str(conflict) for conflict in conflicts]


@transaction.atomic
def create_reservation(
    *,
    tenant_id,
    property_obj: Property,
    guest,
    check_in: date,
    check_out: date,
    agent=None,
    status=ReservationStatus.CONFIRMED,
    created_by=None,
) -> Reservation:
    if property_obj.tenant_id != tenant_id:
        raise serializers.ValidationError({"property_id": "Property does not belong to tenant."})

    if guest.tenant_id != tenant_id:
        raise serializers.ValidationError({"guest_id": "Guest does not belong to tenant."})

    if guest.type != ContactType.GUEST:
        raise serializers.ValidationError({"guest_id": "Contact must be of type GUEST."})

    if agent:
        if agent.tenant_id != tenant_id:
            raise serializers.ValidationError({"agent_id": "Agent does not belong to tenant."})
        if agent.type != ContactType.AGENT:
            raise serializers.ValidationError({"agent_id": "Agent contact must be type AGENT."})

    available, conflicts = check_availability(
        tenant_id=tenant_id,
        property_id=property_obj.id,
        check_in=check_in,
        check_out=check_out,
    )
    if not available:
        raise serializers.ValidationError(
            {
                "detail": "Property is not available for the selected dates.",
                "conflicting_reservation_ids": conflicts,
            }
        )

    quote = calculate_quote(property_obj=property_obj, check_in=check_in, check_out=check_out)

    reservation = Reservation.objects.create(
        tenant_id=tenant_id,
        property=property_obj,
        guest=guest,
        agent=agent,
        check_in=check_in,
        check_out=check_out,
        nights=quote.nights,
        subtotal_amount=quote.subtotal_amount,
        cleaning_fee=quote.cleaning_fee,
        total_amount=quote.total_amount,
        status=status,
        created_by=created_by,
    )
    return reservation
