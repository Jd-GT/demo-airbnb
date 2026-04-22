from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .constants import ModuleKey, PermissionLevel
from .models import Tenant, TenantRole, User
from .permissions import TenantModulePermission
from .serializers import (
    IntegrationItemSerializer,
    TenantCreateSerializer,
    TenantRoleSerializer,
    TenantSerializer,
    TenantUserCreateSerializer,
    TenantUserSerializer,
    TenantUserUpdateSerializer,
    UserRegistrationSerializer,
)
from .services import normalize_integrations_config
from rest_framework_simplejwt.tokens import RefreshToken


class UserRegistrationView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = serializer.save()
        
        # Generate tokens for the created user
        user = User.objects.get(email=result['user']['email'])
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'tenant': result['tenant'],
            'user': result['user'],
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'message': result['message']
        })


class TenantViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
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
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'create':
            return TenantCreateSerializer
        if self.action in {'update', 'partial_update'}:
            return TenantSerializer
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
    lookup_url_kwarg = 'role_id'

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs['tenant_id'])

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
    lookup_url_kwarg = 'user_id'

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs['tenant_id'])

    def get_queryset(self):
        return User.objects.filter(tenant=self.get_tenant()).select_related('role')

    def get_serializer_class(self):
        if self.action == 'create':
            return TenantUserCreateSerializer
        if self.action in {'partial_update', 'update'}:
            return TenantUserUpdateSerializer
        return TenantUserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['tenant'] = self.get_tenant()
        return context

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class TenantIntegrationsView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.CORE.value
    required_permission_level = PermissionLevel.READ
    serializer_class = IntegrationItemSerializer

    def get(self, request, tenant_id):
        tenant = get_object_or_404(Tenant, id=tenant_id)
        serializer = self.get_serializer(
            normalize_integrations_config(tenant.integration_config),
            many=True,
        )
        return Response(serializer.data)
