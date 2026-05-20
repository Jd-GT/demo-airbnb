"""Operations: housekeeping/maintenance Tasks + MessageTemplates."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantAwareModel


class TaskType(models.TextChoices):
    CLEANING = 'CLEANING', 'Limpieza'
    MAINTENANCE = 'MAINTENANCE', 'Mantenimiento'
    INSPECTION = 'INSPECTION', 'Inspección'
    OTHER = 'OTHER', 'Otra'


class TaskStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pendiente'
    IN_PROGRESS = 'IN_PROGRESS', 'En curso'
    DONE = 'DONE', 'Completada'
    CANCELLED = 'CANCELLED', 'Cancelada'


class Task(TenantAwareModel):
    """Operational work item, typically scoped to a property and a date.

    Cleaning tasks are auto-generated when a Reservation reaches its
    check-out date (or is moved to CHECKED_OUT). The CLEANER role sees
    only the tasks assigned to them and can mark them DONE.
    """

    property = models.ForeignKey(
        'inventory.Property',
        on_delete=models.PROTECT,
        related_name='tasks',
    )
    reservation = models.ForeignKey(
        'booking.Reservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        help_text='Optional link to the reservation that triggered the task.',
    )
    type = models.CharField(
        max_length=12,
        choices=TaskType.choices,
        default=TaskType.CLEANING.value,
    )
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    due_date = models.DateField()
    assigned_to = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ops_tasks',
    )
    status = models.CharField(
        max_length=12,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING.value,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ops_tasks_created',
    )

    class Meta:
        ordering = ['due_date', '-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'due_date']),
            models.Index(fields=['tenant', 'assigned_to', 'status']),
        ]

    def __str__(self) -> str:
        return f'{self.type} on {self.property.name} ({self.due_date})'


class MessageChannel(models.TextChoices):
    EMAIL = 'EMAIL', 'Email'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    INTERNAL = 'INTERNAL', 'Interno'


class MessageTemplate(TenantAwareModel):
    """Reusable message body with placeholders.

    Supported placeholders (rendered server-side):
      {{guest_name}}, {{property_name}}, {{check_in}}, {{check_out}},
      {{nights}}, {{total_amount}}, {{balance_due}}, {{tenant_name}},
      {{property_address}}, {{reservation_id}}.
    """

    name = models.CharField(max_length=120)
    channel = models.CharField(
        max_length=12, choices=MessageChannel.choices,
        default=MessageChannel.WHATSAPP.value,
    )
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='tenant_unique_template_name'
            ),
        ]

    def __str__(self) -> str:
        return self.name
