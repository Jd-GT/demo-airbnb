from __future__ import annotations

from django.db import models

from apps.core.models import TenantAwareModel


class ICalSyncStatus(models.TextChoices):
    NEVER = "never", "Never"
    OK = "ok", "OK"
    ERROR = "error", "Error"


class PropertyICalFeed(TenantAwareModel):
    """An external iCal feed (Airbnb, Booking.com, etc.) attached to a property."""

    property = models.ForeignKey(
        "inventory.Property",
        on_delete=models.PROTECT,
        related_name="ical_feeds",
    )
    label = models.CharField(max_length=80, help_text="Etiqueta legible: 'Airbnb', 'Booking.com', etc.")
    ical_url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(
        max_length=20, choices=ICalSyncStatus.choices, default=ICalSyncStatus.NEVER
    )
    last_sync_error = models.TextField(blank=True)

    class Meta:
        ordering = ["property__name", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["property", "ical_url"],
                name="ical_feed_unique_property_url",
            )
        ]

    def __str__(self) -> str:
        return f"{self.property.name} - {self.label}"
