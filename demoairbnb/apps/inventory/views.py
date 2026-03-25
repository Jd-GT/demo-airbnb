from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets

from apps.core.constants import ModuleKey
from apps.core.permissions import TenantModulePermission
from apps.core.models import Tenant
from apps.finance.services import resolve_year_month

from .models import Amenity, Property
from .serializers import AmenitySerializer, PropertySerializer


class TenantScopedViewSetMixin:
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.INVENTORY.value

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs["tenant_id"])


class AmenityViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = AmenitySerializer
    lookup_url_kwarg = "amenity_id"

    def get_queryset(self):
        return Amenity.all_objects.filter(tenant_id=self.kwargs["tenant_id"])

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant())


class PropertyViewSet(TenantScopedViewSetMixin, viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    lookup_url_kwarg = "property_id"

    def get_queryset(self):
        return Property.all_objects.filter(tenant_id=self.kwargs["tenant_id"]).prefetch_related("amenities")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant_id"] = self.kwargs["tenant_id"]
        year, month = resolve_year_month(self.request.query_params)
        context["year"] = year
        context["month"] = month
        return context

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant())
