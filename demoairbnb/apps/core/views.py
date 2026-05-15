from __future__ import annotations

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import Throttled
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .constants import ModuleKey, PermissionLevel
from .integrations import (
    GoogleCalendarCredential,
    get_adapter_for_tenant,
)
from .models import (
    InvitationCode,
    InvitationCodePurpose,
    Tenant,
    TenantRole,
    User,
)
from .permissions import TenantModulePermission
from .serializers import (
    GoogleCalendarCredentialSerializer,
    IntegrationItemSerializer,
    InvitationCodeCreateSerializer,
    InvitationCodeSerializer,
    TenantRoleSerializer,
    TenantSerializer,
    TenantUserCreateSerializer,
    TenantUserSerializer,
    TenantUserUpdateSerializer,
    UserRegistrationSerializer,
)
from .services import normalize_integrations_config


class CurrentUserView(GenericAPIView):
    """Returns the authenticated user's profile + tenant context.

    Used by the frontend on bootstrap so it can decide which sections of the
    UI to show based on `permissions` without leaking other users' data.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TenantUserSerializer

    def get(self, request):
        user = request.user
        data = TenantUserSerializer(user).data
        tenant_data = None
        if user.tenant_id:
            tenant_data = TenantSerializer(user.tenant).data
        # Effective permission map (resolved against system_role).
        from .constants import ModuleKey, PermissionLevel

        if user.is_superuser or user.is_owner:
            perms = {m.value: PermissionLevel.ADMIN.value for m in ModuleKey}
        elif user.role:
            perms = dict(user.role.permissions)
        else:
            perms = {m.value: PermissionLevel.NONE.value for m in ModuleKey}

        return Response(
            {
                'user': data,
                'tenant': tenant_data,
                'permissions': perms,
            }
        )


def healthz(request):
    """Liveness + DB readiness check. No auth required."""
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:  # noqa: BLE001 — we want any error to mean unhealthy
        db_ok = False
    payload = {'status': 'ok' if db_ok else 'degraded', 'db': db_ok}
    return JsonResponse(payload, status=200 if db_ok else 503)


class RateLimitedTokenObtainPairView(TokenObtainPairView):
    """Login endpoint with rate limiting to slow down brute force.

    10 attempts per minute per IP. Override via DJANGO_LOGIN_RATELIMIT env var.
    """

    @method_decorator(
        ratelimit(key='ip', rate='10/m', method='POST', block=False)
    )
    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            raise Throttled(detail='Demasiados intentos de login. Intenta en 1 minuto.')
        return super().post(request, *args, **kwargs)


class UserRegistrationView(GenericAPIView):
    """Public signup endpoint. Always requires a valid InvitationCode.

    The code itself decides whether the user is creating a new tenant
    (CREATE_TENANT) or joining an existing one (JOIN_TENANT). Without a
    valid code, no signup is possible.

    Rate-limited at 5 successful POSTs / hour / IP to deter automated
    signup attacks even when codes leak.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    @method_decorator(
        ratelimit(key='ip', rate='5/h', method='POST', block=False)
    )
    def post(self, request):
        if getattr(request, 'limited', False):
            raise Throttled(
                detail='Demasiados intentos de registro. Intenta en una hora.'
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        user = User.objects.get(email=result['user']['email'])
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'tenant': result['tenant'],
                'user': result['user'],
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'message': result['message'],
            },
            status=status.HTTP_201_CREATED,
        )


class TenantViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Tenant API. Creation of new tenants is gated through the signup flow
    (which requires a CREATE_TENANT invitation code) or through the Django
    admin. There is no public POST /api/tenants/ endpoint anymore.
    """

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
        return [permissions.IsAuthenticated()]


class InvitationCodeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Tenant-scoped management of JOIN_TENANT codes.

    Owners/admins of a tenant create codes here to invite teammates. The
    super-admin handles CREATE_TENANT codes through the Django admin.
    """

    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.USERS.value
    required_permission_level = PermissionLevel.ADMIN
    lookup_url_kwarg = 'code_id'

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs['tenant_id'])

    def get_queryset(self):
        tenant = self.get_tenant()
        return InvitationCode.objects.filter(
            tenant=tenant,
            purpose=InvitationCodePurpose.JOIN_TENANT.value,
        ).select_related('role', 'created_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return InvitationCodeCreateSerializer
        return InvitationCodeSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['tenant'] = self.get_tenant()
        ctx['user'] = self.request.user
        return ctx

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])


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
    """User management scoped to a tenant.

    Listing/creating users requires USERS:read or above. A regular MEMBER
    without that level uses /api/me/ to see their own profile instead of
    this endpoint, so they can never enumerate other users.
    """

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


class GoogleCalendarCredentialView(GenericAPIView):
    """GET/PUT the Google Calendar credential for the tenant.

    Only the OWNER (or someone with users:admin) should touch this.
    The refresh_token is write-only; storage is Fernet-encrypted.
    """

    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.USERS.value
    required_permission_level = PermissionLevel.ADMIN
    serializer_class = GoogleCalendarCredentialSerializer

    def get_object(self, tenant_id):
        return GoogleCalendarCredential.all_objects.filter(
            tenant_id=tenant_id
        ).first()

    def get(self, request, tenant_id):
        cred = self.get_object(tenant_id)
        if not cred:
            return Response(
                {
                    'configured': False,
                    'message': (
                        'Aún no se ha configurado Google Calendar. PUT este '
                        'mismo endpoint para guardar un refresh_token.'
                    ),
                }
            )
        return Response(self.get_serializer(cred).data)

    def put(self, request, tenant_id):
        cred = self.get_object(tenant_id)
        if cred:
            serializer = self.get_serializer(cred, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(data={**request.data})
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(tenant_id=tenant_id) if not cred else serializer.save()
        return Response(self.get_serializer(instance).data)

    def delete(self, request, tenant_id):
        cred = self.get_object(tenant_id)
        if cred:
            cred.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoogleCalendarSyncTriggerView(GenericAPIView):
    """Manual trigger of the (stub) Google Calendar sync for one reservation.

    Returns adapter status. Until real OAuth + API wiring exist, the
    response includes `status: "not_configured"` or `"stub_ok"`.
    """

    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.BOOKING.value
    required_permission_level = PermissionLevel.WRITE
    serializer_class = None

    def post(self, request, tenant_id, reservation_id):
        from apps.booking.models import Reservation

        reservation = get_object_or_404(
            Reservation.all_objects, id=reservation_id, tenant_id=tenant_id
        )
        adapter = get_adapter_for_tenant(tenant_id)
        return Response(adapter.sync_reservation(reservation))
