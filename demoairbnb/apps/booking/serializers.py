from __future__ import annotations

from rest_framework import serializers

from apps.crm.models import Contact
from apps.inventory.models import Property

from .models import Reservation, ReservationStatus
from .services import calculate_quote, check_availability, create_reservation


class AvailabilitySerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()

    def validate(self, attrs):
        tenant_id = self.context["tenant_id"]
        property_obj = Property.all_objects.filter(id=attrs["property_id"], tenant_id=tenant_id).first()
        if not property_obj:
            raise serializers.ValidationError({"property_id": "Property not found for tenant."})
        attrs["property_obj"] = property_obj
        return attrs


class QuoteSerializer(AvailabilitySerializer):
    def create(self, validated_data):
        quote = calculate_quote(
            property_obj=validated_data["property_obj"],
            check_in=validated_data["check_in"],
            check_out=validated_data["check_out"],
        )
        return quote


class ReservationSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    guest_name = serializers.CharField(source="guest.name", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "property",
            "property_name",
            "guest",
            "guest_name",
            "agent",
            "check_in",
            "check_out",
            "nights",
            "subtotal_amount",
            "cleaning_fee",
            "total_amount",
            "status",
            "source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "nights",
            "subtotal_amount",
            "cleaning_fee",
            "total_amount",
            "source",
            "created_at",
            "updated_at",
        ]


class ReservationCreateSerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    guest_id = serializers.UUIDField()
    agent_id = serializers.UUIDField(required=False, allow_null=True)
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    status = serializers.ChoiceField(
        choices=[ReservationStatus.DRAFT, ReservationStatus.CONFIRMED, ReservationStatus.CANCELLED],
        default=ReservationStatus.CONFIRMED,
    )

    def validate(self, attrs):
        tenant_id = self.context["tenant_id"]

        property_obj = Property.all_objects.filter(id=attrs["property_id"], tenant_id=tenant_id).first()
        if not property_obj:
            raise serializers.ValidationError({"property_id": "Property not found for tenant."})

        guest = Contact.all_objects.filter(id=attrs["guest_id"], tenant_id=tenant_id).first()
        if not guest:
            raise serializers.ValidationError({"guest_id": "Guest contact not found for tenant."})

        agent = None
        agent_id = attrs.get("agent_id")
        if agent_id:
            agent = Contact.all_objects.filter(id=agent_id, tenant_id=tenant_id).first()
            if not agent:
                raise serializers.ValidationError({"agent_id": "Agent contact not found for tenant."})

        attrs["property_obj"] = property_obj
        attrs["guest"] = guest
        attrs["agent"] = agent
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        tenant_id = self.context["tenant_id"]
        validated_data.pop("property_id")
        validated_data.pop("guest_id")
        validated_data.pop("agent_id", None)
        return create_reservation(tenant_id=tenant_id, created_by=request.user, **validated_data)

    def to_representation(self, instance):
        return ReservationSerializer(instance).data
