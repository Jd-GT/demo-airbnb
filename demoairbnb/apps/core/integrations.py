"""External-integration models and adapter stubs.

Currently scaffolded:

- GoogleCalendarCredential: per-tenant storage of an OAuth refresh_token
  (encrypted with Fernet) plus the chosen calendar_id. The actual OAuth
  flow and the sync worker are not implemented yet; see
  `documentacion/NEXT_STEPS.md`. The adapter exposes a stable interface so
  the rest of the codebase can call `sync_reservation_to_google()` without
  caring whether it's real or a no-op.

Design follows the Ports & Adapters pattern described in ARCHITECTURE.md.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import models

from .crypto import decrypt_secret, encrypt_secret
from .models import TenantAwareModel

if TYPE_CHECKING:
    from apps.booking.models import Reservation

logger = logging.getLogger(__name__)


class GoogleCalendarCredential(TenantAwareModel):
    """Per-tenant Google Calendar OAuth credentials.

    `refresh_token_encrypted` stores the Fernet-encrypted refresh token.
    Always read via `get_refresh_token()` / write via `set_refresh_token()`.
    """

    calendar_id = models.CharField(
        max_length=200, blank=True,
        help_text='Google calendar identifier (default = primary). '
        'Configure from Google Calendar → Settings → Calendar ID.',
    )
    refresh_token_encrypted = models.TextField(blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=20, default='never')
    last_sync_error = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        app_label = 'core'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant'], name='unique_google_cred_per_tenant'
            )
        ]

    def __str__(self) -> str:
        return f'Google Calendar credential for {self.tenant.subdomain}'

    def set_refresh_token(self, plain: str | None) -> None:
        self.refresh_token_encrypted = encrypt_secret(plain) or ''

    def get_refresh_token(self) -> str | None:
        return decrypt_secret(self.refresh_token_encrypted) if self.refresh_token_encrypted else None


# ---------- Adapter / port ----------

class GoogleCalendarAdapter:
    """Stub adapter. Real OAuth + API calls will be wired later.

    Method signatures are stable so callers can be written against them
    today. Each method short-circuits with a `not_implemented` status when
    there are no credentials, so the booking flow never breaks.
    """

    def __init__(self, credential: GoogleCalendarCredential | None):
        self.credential = credential

    @property
    def is_configured(self) -> bool:
        return bool(
            self.credential
            and self.credential.is_active
            and self.credential.refresh_token_encrypted
        )

    def sync_reservation(self, reservation: 'Reservation') -> dict:
        if not self.is_configured:
            return {
                'status': 'not_configured',
                'reservation_id': str(reservation.id),
            }
        # Real implementation would:
        #   1. Use refresh_token to obtain an access_token.
        #   2. PATCH/POST against the Calendar API to create/update event.
        # For now we log and return ok so the rest of the flow proceeds.
        logger.info(
            'Would sync reservation %s to Google calendar %s',
            reservation.id,
            self.credential.calendar_id,
        )
        return {
            'status': 'stub_ok',
            'reservation_id': str(reservation.id),
            'calendar_id': self.credential.calendar_id,
        }


def get_adapter_for_tenant(tenant_id) -> GoogleCalendarAdapter:
    credential = GoogleCalendarCredential.all_objects.filter(
        tenant_id=tenant_id
    ).first()
    return GoogleCalendarAdapter(credential)
