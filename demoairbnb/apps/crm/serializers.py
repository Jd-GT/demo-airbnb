from __future__ import annotations

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
        return attrs


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
