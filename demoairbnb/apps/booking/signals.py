"""Booking signals.

Push reservation changes to connected third-party integrations (currently Google
Calendar) after the database transaction commits. Failures are logged but never
propagated, so a flaky integration never blocks reservation CRUD.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Reservation

logger = logging.getLogger(__name__)


def _sync_to_google(reservation_id, tenant_id) -> None:
    from apps.core.models import GoogleCalendarCredential
    from apps.core.integrations import GoogleCalendarAdapter

    credential = (
        GoogleCalendarCredential.objects.filter(tenant_id=tenant_id, is_active=True)
        .select_related("tenant")
        .first()
    )
    if credential is None:
        return

    reservation = (
        Reservation.all_objects.select_related("property", "guest")
        .filter(id=reservation_id)
        .first()
    )
    if reservation is None:
        return

    try:
        GoogleCalendarAdapter(credential).sync_reservation(reservation)
    except Exception:
        logger.exception(
            "Failed to sync reservation %s to Google Calendar for tenant %s",
            reservation_id,
            tenant_id,
        )


@receiver(post_save, sender=Reservation)
def reservation_post_save(sender, instance: Reservation, created: bool, **kwargs):
    reservation_id = instance.id
    tenant_id = instance.tenant_id
    transaction.on_commit(lambda: _sync_to_google(reservation_id, tenant_id))


@receiver(post_delete, sender=Reservation)
def reservation_post_delete(sender, instance: Reservation, **kwargs):
    """If a reservation is hard-deleted, remove the matching Google event."""
    from apps.core.models import GoogleCalendarCredential
    from apps.core.integrations import GoogleCalendarAdapter

    reservation_id = instance.id
    tenant_id = instance.tenant_id

    def _delete_event():
        credential = GoogleCalendarCredential.objects.filter(
            tenant_id=tenant_id, is_active=True
        ).first()
        if credential is None:
            return
        try:
            adapter = GoogleCalendarAdapter(credential)
            service = adapter._service()
            results = (
                service.events()
                .list(
                    calendarId=credential.calendar_id or "primary",
                    privateExtendedProperty=f"demoairbnb_reservation_id={reservation_id}",
                    maxResults=1,
                    singleEvents=True,
                )
                .execute()
            )
            items = results.get("items", [])
            if items:
                service.events().delete(
                    calendarId=credential.calendar_id or "primary",
                    eventId=items[0]["id"],
                ).execute()
        except Exception:
            logger.exception(
                "Failed to delete Google Calendar event for reservation %s", reservation_id
            )

    transaction.on_commit(_delete_event)
