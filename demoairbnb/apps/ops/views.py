"""Ops views: tasks, templates, voucher PDF."""

from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.booking.models import Reservation
from apps.core.constants import ModuleKey, PermissionLevel
from apps.core.permissions import TenantModulePermission

from .models import MessageTemplate, Task, TaskStatus
from .serializers import (
    MessageTemplateSerializer,
    RenderMessageInputSerializer,
    RenderedMessageSerializer,
    TaskSerializer,
    TaskStatusUpdateSerializer,
)
from .services import build_voucher_pdf, render_message_for_reservation


class _OpsTaskPermission(TenantModulePermission):
    """Like TenantModulePermission, but lets CLEANER users through.

    The viewset queryset+actions enforce that a CLEANER can only see
    and update tasks assigned to them.
    """

    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated and getattr(user, 'system_role', '') == 'CLEANER':
            tenant_id = view.kwargs.get('tenant_id')
            if tenant_id and str(user.tenant_id) == str(tenant_id):
                return True
        return super().has_permission(request, view)


class TenantScopedOpsMixin:
    permission_classes = [permissions.IsAuthenticated, _OpsTaskPermission]
    permission_module = ModuleKey.BOOKING.value

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['tenant_id'] = self.kwargs['tenant_id']
        return ctx


class TaskViewSet(
    TenantScopedOpsMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Operational tasks (cleaning, maintenance, ...).

    Filter params (all optional):
      ?status=PENDING|IN_PROGRESS|DONE|CANCELLED
      ?assigned_to_me=1   → only tasks assigned to the current user (CLEANER view)
      ?due_from=YYYY-MM-DD
      ?due_to=YYYY-MM-DD
    """

    serializer_class = TaskSerializer
    lookup_url_kwarg = 'task_id'

    def get_queryset(self):
        qs = Task.all_objects.filter(
            tenant_id=self.kwargs['tenant_id']
        ).select_related('property', 'assigned_to')

        params = self.request.query_params
        if status_filter := params.get('status'):
            qs = qs.filter(status=status_filter)
        if params.get('assigned_to_me') in {'1', 'true', 'True'}:
            qs = qs.filter(assigned_to=self.request.user)
        if due_from := params.get('due_from'):
            qs = qs.filter(due_date__gte=due_from)
        if due_to := params.get('due_to'):
            qs = qs.filter(due_date__lte=due_to)

        # CLEANERS can only see their own tasks regardless of params.
        if self.request.user.system_role == 'CLEANER':
            qs = qs.filter(assigned_to=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.kwargs['tenant_id'],
            created_by=self.request.user,
        )

    def partial_update(self, request, *args, **kwargs):
        # Allow CLEANER to mark their own task as IN_PROGRESS / DONE only.
        instance = self.get_object()
        if request.user.system_role == 'CLEANER':
            if instance.assigned_to_id != request.user.id:
                raise ValidationError(
                    {'detail': 'Only the assignee can update this task.'}
                )
            allowed = {TaskStatus.IN_PROGRESS.value, TaskStatus.DONE.value}
            new_status = request.data.get('status')
            if new_status and new_status not in allowed:
                raise ValidationError(
                    {'status': 'Cleaners can only set IN_PROGRESS or DONE.'}
                )

        new_status = request.data.get('status')
        if new_status == TaskStatus.DONE.value and not instance.completed_at:
            request.data._mutable = True if hasattr(request.data, '_mutable') else None
            instance.completed_at = timezone.now()
            instance.save(update_fields=['completed_at'])
        return super().partial_update(request, *args, **kwargs)


class TaskCompleteView(TenantScopedOpsMixin, GenericAPIView):
    """Convenience endpoint: POST .../tasks/<id>/complete/ marks a task DONE."""

    serializer_class = TaskStatusUpdateSerializer

    def post(self, request, tenant_id, task_id):
        task = get_object_or_404(
            Task.all_objects, id=task_id, tenant_id=tenant_id
        )
        if request.user.system_role == 'CLEANER' and task.assigned_to_id != request.user.id:
            raise ValidationError({'detail': 'Only the assignee can mark this task done.'})
        task.status = TaskStatus.DONE.value
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at', 'updated_at'])
        return Response(TaskSerializer(task).data)


class MessageTemplateViewSet(
    TenantScopedOpsMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MessageTemplateSerializer
    lookup_url_kwarg = 'template_id'

    def get_queryset(self):
        return MessageTemplate.all_objects.filter(tenant_id=self.kwargs['tenant_id'])

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.kwargs['tenant_id'])


class RenderReservationMessageView(TenantScopedOpsMixin, GenericAPIView):
    """Render a MessageTemplate against a Reservation. Returns rendered text.

    Does NOT actually send anything (no email/whatsapp integration). The
    frontend can copy the body to clipboard or use a deep link to wa.me.
    """

    serializer_class = RenderedMessageSerializer

    def post(self, request, tenant_id):
        payload = RenderMessageInputSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        template = MessageTemplate.all_objects.filter(
            tenant_id=tenant_id, id=payload.validated_data['template_id']
        ).first()
        if not template:
            raise ValidationError({'template_id': 'Template not found for tenant.'})
        reservation = Reservation.all_objects.filter(
            tenant_id=tenant_id, id=payload.validated_data['reservation_id']
        ).first()
        if not reservation:
            raise ValidationError({'reservation_id': 'Reservation not found for tenant.'})
        rendered = render_message_for_reservation(template, reservation)
        return Response(rendered, status=status.HTTP_200_OK)


class VoucherPDFView(TenantScopedOpsMixin, GenericAPIView):
    """Download an A4 PDF voucher for a reservation."""

    required_permission_level = PermissionLevel.READ
    serializer_class = None

    def get(self, request, tenant_id, reservation_id):
        reservation = get_object_or_404(
            Reservation.all_objects.select_related(
                'guest', 'property', 'tenant'
            ).prefetch_related('lines'),
            id=reservation_id,
            tenant_id=tenant_id,
        )
        try:
            data = build_voucher_pdf(reservation)
        except RuntimeError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="voucher_{reservation.id}.pdf"'
        )
        return response
