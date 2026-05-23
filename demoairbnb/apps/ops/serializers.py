"""Ops serializers: Task, MessageTemplate, render-message endpoint."""

from __future__ import annotations

from rest_framework import serializers

from apps.booking.models import Reservation

from .models import MessageChannel, MessageTemplate, Task, TaskStatus, TaskType


class TaskSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    assigned_to_name = serializers.CharField(
        source='assigned_to.full_name', read_only=True, default=None
    )

    class Meta:
        model = Task
        fields = [
            'id',
            'property',
            'property_name',
            'reservation',
            'type',
            'title',
            'notes',
            'due_date',
            'assigned_to',
            'assigned_to_name',
            'status',
            'completed_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'property_name',
            'assigned_to_name',
            'completed_at',
            'created_at',
        ]


class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c[0] for c in TaskStatus.choices])
    notes = serializers.CharField(required=False, allow_blank=True)


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = [
            'id',
            'name',
            'channel',
            'subject',
            'body',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RenderMessageInputSerializer(serializers.Serializer):
    template_id = serializers.UUIDField()
    reservation_id = serializers.UUIDField()


class RenderedMessageSerializer(serializers.Serializer):
    channel = serializers.CharField()
    subject = serializers.CharField()
    body = serializers.CharField()
