from __future__ import annotations

from rest_framework import serializers

from .models import Amenity, Property


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ["id", "name", "icon_key", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertySerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(read_only=True, many=True)
    amenity_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True,
        allow_empty=True,
    )

    class Meta:
        model = Property
        fields = [
            "id",
            "name",
            "address",
            "capacity_adults",
            "capacity_kids",
            "base_price",
            "cleaning_fee",
            "amenities",
            "amenity_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "amenities"]

    def validate_amenity_ids(self, amenity_ids):
        tenant_id = self.context["tenant_id"]
        if not amenity_ids:
            return amenity_ids
        found_ids = set(
            Amenity.all_objects.filter(tenant_id=tenant_id, id__in=amenity_ids).values_list("id", flat=True)
        )
        missing = [str(amenity_id) for amenity_id in amenity_ids if amenity_id not in found_ids]
        if missing:
            raise serializers.ValidationError(
                f"Amenities not found for tenant: {', '.join(missing)}"
            )
        return amenity_ids

    def create(self, validated_data):
        amenity_ids = validated_data.pop("amenity_ids", [])
        property_obj = Property.objects.create(**validated_data)
        if amenity_ids:
            amenities = Amenity.all_objects.filter(id__in=amenity_ids)
            property_obj.amenities.set(amenities)
        return property_obj

    def update(self, instance, validated_data):
        amenity_ids = validated_data.pop("amenity_ids", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if amenity_ids is not None:
            amenities = Amenity.all_objects.filter(id__in=amenity_ids)
            instance.amenities.set(amenities)
        return instance
