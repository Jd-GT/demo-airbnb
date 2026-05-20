from __future__ import annotations

from rest_framework import serializers

from apps.inventory.models import Property

from .models import PropertyICalFeed


class PropertyICalFeedSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = PropertyICalFeed
        fields = [
            "id",
            "property",
            "property_name",
            "label",
            "ical_url",
            "is_active",
            "last_synced_at",
            "last_sync_status",
            "last_sync_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "property_name",
            "last_synced_at",
            "last_sync_status",
            "last_sync_error",
            "created_at",
            "updated_at",
        ]

    def validate_property(self, value: Property) -> Property:
        tenant_id = self.context.get("tenant_id")
        if value.tenant_id != tenant_id:
            raise serializers.ValidationError("Property does not belong to this tenant.")
        return value
