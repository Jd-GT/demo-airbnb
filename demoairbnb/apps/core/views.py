from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, viewsets

from .constants import ModuleKey
from .models import Tenant, TenantRole, User
from .permissions import TenantModulePermission
from .serializers import (
    TenantCreateSerializer,
    TenantRoleSerializer,
    TenantSerializer,
    TenantUserCreateSerializer,
    TenantUserSerializer,
    TenantUserUpdateSerializer,
)


class TenantViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Tenant.objects.all()
        if user.is_authenticated and user.tenant_id:
            return Tenant.objects.filter(id=user.tenant_id)
        return Tenant.objects.none()

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return TenantCreateSerializer
        return TenantSerializer


class TenantRoleViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TenantRoleSerializer
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.USERS.value
    lookup_url_kwarg = "role_id"

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs["tenant_id"])

    def get_queryset(self):
        return TenantRole.all_objects.filter(tenant=self.get_tenant())

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant())


class TenantUserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.USERS.value
    lookup_url_kwarg = "user_id"

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs["tenant_id"])

    def get_queryset(self):
        return User.objects.filter(tenant=self.get_tenant()).select_related("role")

    def get_serializer_class(self):
        if self.action == "create":
            return TenantUserCreateSerializer
        if self.action in {"partial_update", "update"}:
            return TenantUserUpdateSerializer
        return TenantUserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant"] = self.get_tenant()
        return context

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)
