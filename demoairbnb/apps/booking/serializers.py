from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.crm.models import Contact
from apps.finance.models import Tax
from apps.inventory.models import Property

from .models import (
    PriceRule,
    Reservation,
    ReservationLine,
    ReservationLineType,
    ReservationStatus,
)
from .services import calculate_quote, create_reservation


# ---------- Quote / Availability ----------

class AvailabilitySerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()

    def validate(self, attrs):
        tenant_id = self.context['tenant_id']
        property_obj = Property.all_objects.filter(
            id=attrs['property_id'], tenant_id=tenant_id
        ).first()
        if not property_obj:
            raise serializers.ValidationError(
                {'property_id': 'Property not found for tenant.'}
            )
        attrs['property_obj'] = property_obj
        return attrs


class QuoteSerializer(AvailabilitySerializer):
    def create(self, validated_data):
        return calculate_quote(
            property_obj=validated_data['property_obj'],
            check_in=validated_data['check_in'],
            check_out=validated_data['check_out'],
        )


# ---------- Reservation lines ----------

class ReservationLineSerializer(serializers.ModelSerializer):
    line_subtotal = serializers.SerializerMethodField()
    line_tax_total = serializers.SerializerMethodField()
    tax_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        source='taxes',
        queryset=Tax.all_objects.all(),
    )

    class Meta:
        model = ReservationLine
        fields = [
            'id',
            'reservation',
            'type',
            'description',
            'quantity',
            'unit_price',
            'taxes',
            'tax_ids',
            'line_subtotal',
            'line_tax_total',
            'created_at',
        ]
        read_only_fields = [
            'id', 'taxes', 'line_subtotal', 'line_tax_total', 'created_at',
        ]

    def get_line_subtotal(self, obj) -> str:
        return str(obj.line_subtotal)

    def get_line_tax_total(self, obj) -> str:
        return str(obj.line_tax_total())


# ---------- Reservation ----------

class ReservationSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    guest_name = serializers.CharField(source='guest.name', read_only=True)
    agent_name = serializers.CharField(source='agent.name', read_only=True, default=None)
    balance_due = serializers.SerializerMethodField()
    lines = ReservationLineSerializer(many=True, read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id',
            'property',
            'property_name',
            'guest',
            'guest_name',
            'agent',
            'agent_name',
            'check_in',
            'check_out',
            'nights',
            'subtotal_amount',
            'cleaning_fee',
            'tax_total',
            'total_amount',
            'amount_paid',
            'balance_due',
            'extras_received',
            'agent_commission',
            'status',
            'payment_status',
            'lines',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'nights',
            'subtotal_amount',
            'cleaning_fee',
            'tax_total',
            'total_amount',
            'amount_paid',
            'balance_due',
            'extras_received',
            'agent_commission',
            'payment_status',
            'lines',
            'created_at',
            'updated_at',
        ]

    def get_balance_due(self, obj) -> str:
        return str(obj.get_balance_due())


class ReservationCreateSerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    guest_id = serializers.UUIDField()
    agent_id = serializers.UUIDField(required=False, allow_null=True)
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    status = serializers.ChoiceField(
        choices=[c[0] for c in ReservationStatus.choices],
        default=ReservationStatus.CONFIRMED.value,
    )

    def validate(self, attrs):
        tenant_id = self.context['tenant_id']

        property_obj = Property.all_objects.filter(
            id=attrs['property_id'], tenant_id=tenant_id
        ).first()
        if not property_obj:
            raise serializers.ValidationError(
                {'property_id': 'Property not found for tenant.'}
            )

        guest = Contact.all_objects.filter(
            id=attrs['guest_id'], tenant_id=tenant_id
        ).first()
        if not guest:
            raise serializers.ValidationError(
                {'guest_id': 'Guest contact not found for tenant.'}
            )

        agent = None
        agent_id = attrs.get('agent_id')
        if agent_id:
            agent = Contact.all_objects.filter(id=agent_id, tenant_id=tenant_id).first()
            if not agent:
                raise serializers.ValidationError(
                    {'agent_id': 'Agent contact not found for tenant.'}
                )

        attrs['property_obj'] = property_obj
        attrs['guest'] = guest
        attrs['agent'] = agent
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        tenant_id = self.context['tenant_id']
        validated_data.pop('property_id')
        validated_data.pop('guest_id')
        validated_data.pop('agent_id', None)
        return create_reservation(
            tenant_id=tenant_id, created_by=request.user, **validated_data
        )

    def to_representation(self, instance):
        return ReservationSerializer(instance).data


# ---------- PriceRule ----------

class PriceRuleSerializer(serializers.ModelSerializer):
    property_ids = serializers.PrimaryKeyRelatedField(
        source='properties',
        many=True,
        queryset=Property.all_objects.all(),
        required=False,
    )

    class Meta:
        model = PriceRule
        fields = [
            'id',
            'name',
            'start_date',
            'end_date',
            'is_percent',
            'modifier',
            'min_nights',
            'priority',
            'property_ids',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        if attrs.get('end_date') and attrs.get('start_date'):
            if attrs['end_date'] < attrs['start_date']:
                raise serializers.ValidationError(
                    {'end_date': 'end_date must be on or after start_date.'}
                )
        if attrs.get('modifier', Decimal('0')) <= 0:
            raise serializers.ValidationError(
                {'modifier': 'modifier must be a positive value.'}
            )
        return attrs
