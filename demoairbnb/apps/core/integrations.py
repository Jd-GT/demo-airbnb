"""Third-party integration adapters.

Currently provides a Google Calendar adapter that uses a stored refresh token
(encrypted with Fernet) to push reservation events into the tenant's calendar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .crypto import decrypt_str, encrypt_str
# Re-exported for backwards-compatible imports.
from .models import GoogleCalendarCredential  # noqa: F401

if TYPE_CHECKING:
    from apps.booking.models import Reservation


logger = logging.getLogger(__name__)

GOOGLE_STATE_SALT = "google-calendar-oauth"
GOOGLE_STATE_MAX_AGE_SECONDS = 600


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def _signer() -> TimestampSigner:
    return TimestampSigner(salt=GOOGLE_STATE_SALT)


def sign_state(tenant_id: str) -> str:
    return _signer().sign(str(tenant_id))


def unsign_state(state: str) -> str:
    try:
        return _signer().unsign(state, max_age=GOOGLE_STATE_MAX_AGE_SECONDS)
    except SignatureExpired as exc:
        raise ValueError("OAuth state expired. Restart the connection flow.") from exc
    except BadSignature as exc:
        raise ValueError("Invalid OAuth state.") from exc


@dataclass
class OAuthExchangeResult:
    refresh_token: str
    access_token: str
    account_email: str


class GoogleCalendarAdapter:
    """Thin wrapper around the Google Calendar API for a single tenant credential."""

    def __init__(self, credential: "GoogleCalendarCredential"):
        self.credential = credential

    # --- OAuth lifecycle ---------------------------------------------------

    @staticmethod
    def build_authorization_url(tenant_id: str) -> str:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise RuntimeError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET in the environment."
            )
        flow = Flow.from_client_config(
            _client_config(),
            scopes=settings.GOOGLE_OAUTH_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=sign_state(tenant_id),
        )
        return auth_url

    @staticmethod
    def exchange_code(code: str) -> OAuthExchangeResult:
        flow = Flow.from_client_config(
            _client_config(),
            scopes=settings.GOOGLE_OAUTH_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        if not creds.refresh_token:
            raise RuntimeError(
                "Google did not return a refresh token. Revoke previous access "
                "in https://myaccount.google.com/permissions and retry."
            )

        account_email = ""
        try:
            service = build("oauth2", "v2", credentials=creds, cache_discovery=False)
            account_email = service.userinfo().get().execute().get("email", "") or ""
        except Exception:
            logger.exception("Failed to fetch Google account email after OAuth exchange")

        return OAuthExchangeResult(
            refresh_token=creds.refresh_token,
            access_token=creds.token or "",
            account_email=account_email,
        )

    # --- Calendar sync -----------------------------------------------------

    def _build_credentials(self) -> Credentials:
        refresh_token = decrypt_str(self.credential.refresh_token_encrypted)
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=settings.GOOGLE_OAUTH_SCOPES,
        )
        creds.refresh(GoogleRequest())
        return creds

    def _service(self):
        return build("calendar", "v3", credentials=self._build_credentials(), cache_discovery=False)

    def sync_reservation(self, reservation: "Reservation") -> str:
        """Create or update a Google Calendar event for a reservation.

        Returns the Google event id. Persists last_sync_at/status on the credential.
        """
        from apps.booking.models import ReservationStatus

        try:
            service = self._service()
            event_body = self._reservation_to_event(reservation)
            existing_event_id = self._lookup_existing_event_id(reservation)

            calendar_id = self.credential.calendar_id or "primary"

            if reservation.status == ReservationStatus.CANCELLED and existing_event_id:
                service.events().delete(
                    calendarId=calendar_id, eventId=existing_event_id
                ).execute()
                event_id = ""
            elif existing_event_id:
                event = (
                    service.events()
                    .update(calendarId=calendar_id, eventId=existing_event_id, body=event_body)
                    .execute()
                )
                event_id = event.get("id", existing_event_id)
            else:
                event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
                event_id = event.get("id", "")

            self.credential.last_sync_at = timezone.now()
            self.credential.last_sync_status = "connected"
            self.credential.last_sync_error = ""
            self.credential.save(
                update_fields=["last_sync_at", "last_sync_status", "last_sync_error", "updated_at"]
            )
            return event_id
        except HttpError as exc:
            self._record_failure(str(exc))
            raise
        except Exception as exc:
            self._record_failure(str(exc))
            raise

    def _record_failure(self, message: str) -> None:
        self.credential.last_sync_at = timezone.now()
        self.credential.last_sync_status = "error"
        self.credential.last_sync_error = message[:2000]
        self.credential.save(
            update_fields=["last_sync_at", "last_sync_status", "last_sync_error", "updated_at"]
        )

    def _reservation_to_event(self, reservation: "Reservation") -> dict:
        property_name = getattr(reservation.property, "name", "Property")
        guest_name = getattr(reservation.guest, "name", None) or "Guest"
        return {
            "summary": f"{property_name} - {guest_name}",
            "description": (
                f"Reserva #{reservation.id}\n"
                f"Huésped: {guest_name}\n"
                f"Propiedad: {property_name}\n"
                f"Estado: {reservation.status}\n"
                f"Total: {reservation.total_amount}"
            ),
            "start": {"date": reservation.check_in.isoformat()},
            "end": {"date": reservation.check_out.isoformat()},
            "extendedProperties": {
                "private": {
                    "demoairbnb_reservation_id": str(reservation.id),
                    "demoairbnb_tenant_id": str(reservation.tenant_id),
                }
            },
        }

    def _lookup_existing_event_id(self, reservation: "Reservation") -> Optional[str]:
        try:
            service = self._service()
            results = (
                service.events()
                .list(
                    calendarId=self.credential.calendar_id or "primary",
                    privateExtendedProperty=f"demoairbnb_reservation_id={reservation.id}",
                    maxResults=1,
                    singleEvents=True,
                )
                .execute()
            )
            items = results.get("items", [])
            if items:
                return items[0].get("id")
        except HttpError:
            logger.exception("Failed to look up existing Google Calendar event")
        return None


def save_credential_from_oauth(
    *, tenant, exchange: OAuthExchangeResult, calendar_id: str = "primary"
) -> "GoogleCalendarCredential":
    """Persist an OAuth exchange result as an active credential for the tenant."""
    from .models import GoogleCalendarCredential

    encrypted = encrypt_str(exchange.refresh_token)
    credential, _ = GoogleCalendarCredential.objects.update_or_create(
        tenant=tenant,
        defaults={
            "refresh_token_encrypted": encrypted,
            "calendar_id": calendar_id,
            "google_account_email": exchange.account_email,
            "is_active": True,
            "last_sync_status": "connected",
            "last_sync_at": timezone.now(),
            "last_sync_error": "",
        },
    )
    return credential
