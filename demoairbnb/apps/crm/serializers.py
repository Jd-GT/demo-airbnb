from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Contact, Lead


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'type',
            'commission_rate',
            'tax_id',
            'address',
            'nationality',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        contact_type = attrs.get('type', getattr(self.instance, 'type', None))
        commission_rate = attrs.get(
            'commission_rate', getattr(self.instance, 'commission_rate', 0)
        )
        if contact_type != 'AGENT' and commission_rate:
            attrs['commission_rate'] = 0

        # Pre-check uniqueness so we never let an IntegrityError reach
        # the response handler (which would surface as HTTP 500).
        tenant_id = self.context.get('tenant_id') or (
            self.context.get('view') and self.context['view'].kwargs.get('tenant_id')
        )
        instance_id = getattr(self.instance, 'id', None)
        email = attrs.get('email', getattr(self.instance, 'email', '')) or ''
        tax_id = attrs.get('tax_id', getattr(self.instance, 'tax_id', '')) or ''

        if email and tenant_id:
            qs = Contact.all_objects.filter(tenant_id=tenant_id, email__iexact=email)
            if instance_id:
                qs = qs.exclude(id=instance_id)
            if qs.exists():
                raise serializers.ValidationError(
                    {'email': 'Ya existe un cliente con ese email en esta empresa.'}
                )
        if tax_id and tenant_id:
            qs = Contact.all_objects.filter(tenant_id=tenant_id, tax_id=tax_id)
            if instance_id:
                qs = qs.exclude(id=instance_id)
            if qs.exists():
                raise serializers.ValidationError(
                    {'tax_id': 'Ya existe un cliente con ese ID fiscal.'}
                )
        return attrs

    def create(self, validated_data):
        # Even with the validator above there is a tiny race window;
        # wrap in atomic + IntegrityError handler as defense in depth.
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {'detail': f'Conflicto al guardar el cliente: {exc}'}
            ) from exc

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {'detail': f'Conflicto al actualizar el cliente: {exc}'}
            ) from exc


class ContactStatsSerializer(serializers.Serializer):
    """Aggregate stats for a single contact (used in /clientes detail page)."""

    contact_id = serializers.UUIDField()
    reservations_count = serializers.IntegerField()
    confirmed_reservations_count = serializers.IntegerField()
    cancelled_reservations_count = serializers.IntegerField()
    total_billed = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_lodging_paid = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_extras_paid = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_refunded = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    first_check_in = serializers.DateField(allow_null=True)
    last_check_out = serializers.DateField(allow_null=True)
    nights_total = serializers.IntegerField()


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            'id',
            'contact',
            'source',
            'stage',
            'desired_check_in',
            'desired_check_out',
            'expected_revenue',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        tenant_id = self.context['tenant_id']
        contact = attrs.get('contact', getattr(self.instance, 'contact', None))
        source = attrs.get('source', getattr(self.instance, 'source', None))

        if contact and contact.tenant_id != tenant_id:
            raise serializers.ValidationError(
                {'contact': 'Contact must belong to the same tenant.'}
            )

        if source and source.tenant_id != tenant_id:
            raise serializers.ValidationError(
                {'source': 'Source contact must belong to the same tenant.'}
            )

        check_in = attrs.get(
            'desired_check_in', getattr(self.instance, 'desired_check_in', None)
        )
        check_out = attrs.get(
            'desired_check_out', getattr(self.instance, 'desired_check_out', None)
        )
        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError(
                {'desired_check_out': 'Check-out must be after check-in.'}
            )

        return attrs
