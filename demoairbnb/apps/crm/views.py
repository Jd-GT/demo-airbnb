from __future__ import annotations

from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.core.constants import ModuleKey
from apps.core.permissions import TenantModulePermission

from .models import Contact, Lead
from .serializers import ContactSerializer, ContactStatsSerializer, LeadSerializer
from .services import get_contact_stats


class TenantScopedCRMViewSetMixin:
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.CRM.value


class ContactViewSet(TenantScopedCRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    lookup_url_kwarg = 'contact_id'

    def get_queryset(self):
        queryset = Contact.all_objects.filter(tenant_id=self.kwargs['tenant_id'])
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(phone__icontains=search)
            )
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['tenant_id'] = self.kwargs['tenant_id']
        return context

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.kwargs['tenant_id'])


class ContactStatsView(GenericAPIView):
    """Aggregate stats for one contact: reservations, billed, paid, owed, etc."""

    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.CRM.value
    serializer_class = ContactStatsSerializer

    def get(self, request, tenant_id, contact_id):
        contact = get_object_or_404(
            Contact.all_objects, id=contact_id, tenant_id=tenant_id
        )
        return Response(get_contact_stats(contact))


class LeadViewSet(TenantScopedCRMViewSetMixin, viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    lookup_url_kwarg = 'lead_id'

    def get_queryset(self):
        return Lead.all_objects.filter(
            tenant_id=self.kwargs['tenant_id']
        ).select_related('contact', 'source')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['tenant_id'] = self.kwargs['tenant_id']
        return context

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.kwargs['tenant_id'])
