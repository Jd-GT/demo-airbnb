from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from apps.crm.models import ContactType
from apps.inventory.models import Property

from .models import (
    PriceRule,
    Reservation,
    ReservationLine,
    ReservationLineType,
    ReservationStatus,
)

ACTIVE_BLOCKING_STATUSES = (
    ReservationStatus.DRAFT,
    ReservationStatus.CONFIRMED,
    ReservationStatus.CHECKED_IN,
)


@dataclass(frozen=True)
class QuoteBreakdown:
    nights: int
    nightly_rate: Decimal  # average per night across the stay
    subtotal_amount: Decimal
    cleaning_fee: Decimal
    total_amount: Decimal
    nights_breakdown: list[dict] = field(default_factory=list)
    applied_rule_names: list[str] = field(default_factory=list)
    min_nights_required: int = 1


def _nights_between(check_in: date, check_out: date) -> int:
    nights = (check_out - check_in).days
    if nights <= 0:
        raise serializers.ValidationError(
            {'check_out': 'check_out must be after check_in.'}
        )
    return nights


def _resolve_rate_for_day(
    *, property_obj: Property, day: date, active_rules: list[PriceRule]
) -> tuple[Decimal, PriceRule | None]:
    """Return the nightly rate to charge for a given day.

    Picks the highest-priority active rule that covers the day and applies
    to this property. Falls back to property.base_price.
    """
    base = Decimal(str(property_obj.base_price))
    candidates: list[PriceRule] = []
    for rule in active_rules:
        if not (rule.start_date <= day <= rule.end_date):
            continue
        # property scope: empty = all
        rule_props = list(rule.properties.values_list('id', flat=True))
        if rule_props and property_obj.id not in rule_props:
            continue
        candidates.append(rule)

    if not candidates:
        return base.quantize(Decimal('0.01')), None

    # priority desc, then property-specific over wildcard
    def specificity(r: PriceRule) -> int:
        return 1 if r.properties.exists() else 0

    candidates.sort(key=lambda r: (r.priority, specificity(r)), reverse=True)
    chosen = candidates[0]
    if chosen.is_percent:
        rate = (base * Decimal(chosen.modifier)).quantize(Decimal('0.01'))
    else:
        rate = Decimal(chosen.modifier).quantize(Decimal('0.01'))
    return rate, chosen


def calculate_quote(
    *, property_obj: Property, check_in: date, check_out: date
) -> QuoteBreakdown:
    nights = _nights_between(check_in, check_out)
    cleaning_fee = Decimal(str(property_obj.cleaning_fee))

    active_rules = list(
        PriceRule.all_objects.filter(
            tenant_id=property_obj.tenant_id,
            is_active=True,
            start_date__lte=check_out - timedelta(days=1),
            end_date__gte=check_in,
        ).prefetch_related('properties')
    )

    nights_breakdown: list[dict] = []
    applied_rule_names: list[str] = []
    min_nights_required = 1
    subtotal = Decimal('0')

    current = check_in
    while current < check_out:
        rate, rule = _resolve_rate_for_day(
            property_obj=property_obj, day=current, active_rules=active_rules
        )
        nights_breakdown.append(
            {
                'date': current.isoformat(),
                'rate': str(rate),
                'rule': rule.name if rule else None,
            }
        )
        if rule:
            if rule.name not in applied_rule_names:
                applied_rule_names.append(rule.name)
            min_nights_required = max(min_nights_required, rule.min_nights)
        subtotal += rate
        current = current + timedelta(days=1)

    if nights < min_nights_required:
        raise serializers.ValidationError(
            {
                'detail': (
                    f'These dates require a minimum stay of '
                    f'{min_nights_required} nights (rule: '
                    f'{", ".join(applied_rule_names) or "—"}).'
                )
            }
        )

    nightly_rate = (subtotal / nights).quantize(Decimal('0.01'))
    total = subtotal + cleaning_fee
    return QuoteBreakdown(
        nights=nights,
        nightly_rate=nightly_rate,
        subtotal_amount=subtotal.quantize(Decimal('0.01')),
        cleaning_fee=cleaning_fee.quantize(Decimal('0.01')),
        total_amount=total.quantize(Decimal('0.01')),
        nights_breakdown=nights_breakdown,
        applied_rule_names=applied_rule_names,
        min_nights_required=min_nights_required,
    )


def check_availability(
    *,
    tenant_id,
    property_id,
    check_in: date,
    check_out: date,
    exclude_reservation_id=None,
) -> tuple[bool, list[str]]:
    _nights_between(check_in, check_out)

    overlaps = Q(check_in__lt=check_out) & Q(check_out__gt=check_in)
    query = Reservation.all_objects.filter(
        tenant_id=tenant_id,
        property_id=property_id,
        status__in=ACTIVE_BLOCKING_STATUSES,
    ).filter(overlaps)
    if exclude_reservation_id:
        query = query.exclude(id=exclude_reservation_id)

    conflicts = list(query.values_list('id', flat=True))
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
        raise serializers.ValidationError(
            {'property_id': 'Property does not belong to tenant.'}
        )

    if guest.tenant_id != tenant_id:
        raise serializers.ValidationError(
            {'guest_id': 'Guest does not belong to tenant.'}
        )

    # Accept GUEST (real person) or PLATFORM (e.g. "Airbnb #1234" placeholder
    # contact when we don't yet know the actual guest details). AGENT
    # contacts must be passed via `agent`, not `guest`.
    if guest.type not in (ContactType.GUEST, ContactType.PLATFORM):
        raise serializers.ValidationError(
            {
                'guest_id': (
                    'El titular de la reserva debe ser un Huésped o una '
                    'Plataforma (Airbnb, Booking, etc.). Los agentes van '
                    'en el campo "agent".'
                )
            }
        )

    if agent:
        if agent.tenant_id != tenant_id:
            raise serializers.ValidationError(
                {'agent_id': 'Agent does not belong to tenant.'}
            )
        if agent.type != ContactType.AGENT:
            raise serializers.ValidationError(
                {'agent_id': 'Agent contact must be type AGENT.'}
            )

    available, conflicts = check_availability(
        tenant_id=tenant_id,
        property_id=property_obj.id,
        check_in=check_in,
        check_out=check_out,
    )
    if not available:
        raise serializers.ValidationError(
            {
                'detail': 'Property is not available for the selected dates.',
                'conflicting_reservation_ids': conflicts,
            }
        )

    quote = calculate_quote(
        property_obj=property_obj, check_in=check_in, check_out=check_out
    )

    agent_commission = Decimal('0')
    if agent and agent.commission_rate:
        agent_commission = (
            quote.subtotal_amount * Decimal(agent.commission_rate) / Decimal('100')
        ).quantize(Decimal('0.01'))

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
        tax_total=Decimal('0'),
        total_amount=quote.total_amount,
        amount_paid=Decimal('0'),
        agent_commission=agent_commission,
        status=status,
        created_by=created_by,
    )

    # Auto-generate breakdown lines: one NIGHT line summarising all nights
    # plus a FEE line if there's a cleaning fee. The frontend can later
    # add EXTRA lines manually.
    ReservationLine.objects.create(
        tenant_id=tenant_id,
        reservation=reservation,
        type=ReservationLineType.NIGHT.value,
        description=(
            f'{quote.nights} noche(s) — '
            f'{property_obj.name} '
            f'({", ".join(quote.applied_rule_names) or "tarifa base"})'
        ),
        quantity=Decimal(quote.nights),
        unit_price=quote.nightly_rate,
    )
    if quote.cleaning_fee > 0:
        ReservationLine.objects.create(
            tenant_id=tenant_id,
            reservation=reservation,
            type=ReservationLineType.FEE.value,
            description='Tarifa de limpieza',
            quantity=Decimal('1'),
            unit_price=quote.cleaning_fee,
        )

    # Bookkeeping: if confirmed/checked-in, devengar el ingreso.
    if status in (ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN):
        from apps.finance.services import accrue_reservation_income

        accrue_reservation_income(reservation)

    # Ops: schedule the post-checkout cleaning task.
    from apps.ops.services import ensure_cleaning_task_for_reservation

    ensure_cleaning_task_for_reservation(reservation)

    return reservation


@transaction.atomic
def recompute_reservation_totals(reservation: Reservation) -> Reservation:
    """Recalculate amounts based on current lines (and refresh tax_total)."""
    subtotal = Decimal('0')
    cleaning = Decimal('0')
    tax_total = Decimal('0')
    for line in reservation.lines.all():
        line_sub = line.line_subtotal
        if line.type == ReservationLineType.FEE.value:
            cleaning += line_sub
        elif line.type == ReservationLineType.DISCOUNT.value:
            subtotal -= line_sub
        else:
            subtotal += line_sub
        tax_total += line.line_tax_total()
    reservation.subtotal_amount = subtotal.quantize(Decimal('0.01'))
    reservation.cleaning_fee = cleaning.quantize(Decimal('0.01'))
    reservation.tax_total = tax_total.quantize(Decimal('0.01'))
    reservation.total_amount = (subtotal + cleaning + tax_total).quantize(
        Decimal('0.01')
    )
    reservation.save(
        update_fields=[
            'subtotal_amount',
            'cleaning_fee',
            'tax_total',
            'total_amount',
            'updated_at',
        ]
    )
    return reservation
