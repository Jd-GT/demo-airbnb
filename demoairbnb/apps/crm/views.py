from __future__ import annotations

from django.db import models
from rest_framework import permissions, viewsets

from apps.core.constants import ModuleKey
from apps.core.permissions import TenantModulePermission

from .models import Contact, Lead
from .serializers import ContactSerializer, LeadSerializer


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

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.kwargs['tenant_id'])


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
