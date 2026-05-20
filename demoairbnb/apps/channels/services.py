"""iCal feed synchronization.

Reads an iCal URL from a third-party calendar (Airbnb, Booking.com, ...) and
materializes blocked dates as local ``Reservation`` rows with ``source='ical'``.

Idempotency: existing reservations matching (property, check_in, check_out,
source='ical') are skipped, so re-running is safe.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Iterable

import requests
from django.db import transaction
from django.utils import timezone
from icalendar import Calendar

from apps.booking.models import Reservation, ReservationSource, ReservationStatus
from apps.crm.models import Contact, ContactType

from .models import ICalSyncStatus, PropertyICalFeed

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = (
    "Mozilla/5.0 (compatible; demo-airbnb-ical-sync/1.0; "
    "+https://github.com/Jd-GT/demo-airbnb)"
)

# Heuristic: words that mark a VEVENT as a real platform block to import.
BLOCK_KEYWORDS = (
    "reserved",
    "not available",
    "unavailable",
    "blocked",
    "airbnb",
    "booking",
    "vrbo",
    "homeaway",
    "closed",
)


def _is_block_event(summary: str) -> bool:
    if not summary:
        # Airbnb's iCal sometimes ships VEVENTs without SUMMARY when the slot is
        # just a generic block — treat as blocking.
        return True
    return any(keyword in summary.lower() for keyword in BLOCK_KEYWORDS)


def _to_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _get_or_create_platform_contact(*, tenant, label: str) -> Contact:
    contact = Contact.all_objects.filter(
        tenant=tenant, type=ContactType.PLATFORM, name=label
    ).first()
    if contact:
        return contact
    return Contact.objects.create(
        tenant=tenant,
        name=label,
        type=ContactType.PLATFORM,
    )


def sync_ical_feed(feed: PropertyICalFeed) -> dict:
    """Sync a single iCal feed. Always persists feed status; never re-raises."""
    result: dict = {"created": 0, "skipped": 0, "errors": []}

    try:
        response = requests.get(
            feed.ical_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT, "Accept": "text/calendar, */*"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _record_failure(feed, f"HTTP error: {exc}")
        result["errors"].append(str(exc)[:300])
        return result

    try:
        calendar = Calendar.from_ical(response.content)
    except Exception as exc:  # icalendar raises ValueError or similar
        _record_failure(feed, f"Parse error: {exc}")
        result["errors"].append(str(exc)[:300])
        return result

    events: Iterable = calendar.walk("VEVENT")

    try:
        with transaction.atomic():
            platform_contact = _get_or_create_platform_contact(
                tenant=feed.tenant, label=feed.label
            )

            for event in events:
                summary_raw = event.get("SUMMARY")
                summary = str(summary_raw) if summary_raw is not None else ""

                if not _is_block_event(summary):
                    result["skipped"] += 1
                    continue

                dtstart = event.get("DTSTART")
                dtend = event.get("DTEND")
                if not dtstart or not dtend:
                    result["skipped"] += 1
                    continue

                check_in = _to_date(dtstart.dt)
                check_out = _to_date(dtend.dt)
                if not check_in or not check_out or check_out <= check_in:
                    result["skipped"] += 1
                    continue

                exists = Reservation.all_objects.filter(
                    tenant=feed.tenant,
                    property=feed.property,
                    check_in=check_in,
                    check_out=check_out,
                    source=ReservationSource.ICAL,
                ).exists()
                if exists:
                    result["skipped"] += 1
                    continue

                Reservation.objects.create(
                    tenant=feed.tenant,
                    property=feed.property,
                    guest=platform_contact,
                    check_in=check_in,
                    check_out=check_out,
                    nights=(check_out - check_in).days,
                    subtotal_amount=0,
                    cleaning_fee=0,
                    total_amount=0,
                    status=ReservationStatus.CONFIRMED,
                    source=ReservationSource.ICAL,
                )
                result["created"] += 1
    except Exception as exc:  # noqa: BLE001 — persist error and report; never crash caller
        logger.exception("Unexpected error syncing iCal feed %s", feed.id)
        _record_failure(feed, f"Unexpected error: {exc}")
        result["errors"].append(str(exc)[:300])
        return result

    feed.last_synced_at = timezone.now()
    feed.last_sync_status = ICalSyncStatus.OK
    feed.last_sync_error = ""
    feed.save(
        update_fields=["last_synced_at", "last_sync_status", "last_sync_error", "updated_at"]
    )
    return result


def _record_failure(feed: PropertyICalFeed, message: str) -> None:
    feed.last_synced_at = timezone.now()
    feed.last_sync_status = ICalSyncStatus.ERROR
    feed.last_sync_error = message[:2000]
    feed.save(
        update_fields=["last_synced_at", "last_sync_status", "last_sync_error", "updated_at"]
    )


def sync_all_feeds_for_tenant(tenant) -> dict:
    """Sync every active feed for a tenant. Aggregates per-feed results."""
    feeds = PropertyICalFeed.objects.filter(tenant=tenant, is_active=True).select_related(
        "property", "tenant"
    )
    aggregate = {"feeds": 0, "created": 0, "skipped": 0, "errors": 0, "details": []}
    for feed in feeds:
        result = sync_ical_feed(feed)
        aggregate["feeds"] += 1
        aggregate["created"] += result["created"]
        aggregate["skipped"] += result["skipped"]
        aggregate["errors"] += len(result["errors"])
        aggregate["details"].append(
            {
                "feed_id": str(feed.id),
                "label": feed.label,
                "property": feed.property.name,
                "created": result["created"],
                "skipped": result["skipped"],
                "errors": result["errors"],
                "status": feed.last_sync_status,
            }
        )
    return aggregate
