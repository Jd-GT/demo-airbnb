from __future__ import annotations

from django.contrib import admin

from .models import PropertyICalFeed


@admin.register(PropertyICalFeed)
class PropertyICalFeedAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "property",
        "tenant",
        "is_active",
        "last_sync_status",
        "last_synced_at",
    )
    list_filter = ("is_active", "last_sync_status", "tenant")
    search_fields = ("label", "ical_url", "property__name")
    readonly_fields = ("last_synced_at", "last_sync_status", "last_sync_error", "created_at", "updated_at")
