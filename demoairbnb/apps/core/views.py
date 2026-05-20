from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from django.conf import settings
from django.db import connection
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import Throttled
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .constants import ModuleKey, PermissionLevel
from .integrations import (
    GoogleCalendarAdapter,
    save_credential_from_oauth,
    unsign_state,
)
from .models import (
    EmailTemplate,
    GoogleCalendarCredential,
    InvitationCode,
    InvitationCodePurpose,
    Tenant,
    TenantRole,
    User,
)
from .permissions import TenantModulePermission
from .serializers import (
    IntegrationItemSerializer,
    InvitationCodeCreateSerializer,
    InvitationCodeSerializer,
    PersonalizedTokenObtainPairSerializer,
    TenantRoleSerializer,
    TenantSerializer,
    TenantUserCreateSerializer,
    TenantUserSerializer,
    TenantUserUpdateSerializer,
    UserRegistrationSerializer,
    EmailTemplateCreateSerializer,
    EmailTemplateSerializer,
    EmailTemplateUpdateSerializer,
)
from .services import normalize_integrations_config


class PersonalizedTokenObtainPairView(TokenObtainPairView):
    serializer_class = PersonalizedTokenObtainPairSerializer


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

    serializer_class = PersonalizedTokenObtainPairSerializer

    @method_decorator(
        ratelimit(key='ip', rate='10/m', method='POST', block=False)
    )
    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            raise Throttled(detail='Demasiados intentos de login. Intenta en 1 minuto.')
        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh_token') or request.data.get('refresh')

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                return Response(
                    {'detail': 'Invalid refresh token.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK,
        )


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
        credential = getattr(tenant, "google_calendar_credential", None)
        serializer = self.get_serializer(
            normalize_integrations_config(tenant.integration_config, google_credential=credential),
            many=True,
        )
        return Response(serializer.data)

class GoogleCalendarOAuthInitView(APIView):
    """Return a Google authorization URL so the frontend can redirect the user."""

    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.CORE.value
    required_permission_level = PermissionLevel.WRITE

    def get(self, request, tenant_id):
        tenant = get_object_or_404(Tenant, id=tenant_id)
        try:
            url = GoogleCalendarAdapter.build_authorization_url(str(tenant.id))
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"authorization_url": url})


class GoogleCalendarOAuthCallbackView(APIView):
    """Receive Google's OAuth callback, persist refresh token, redirect to frontend.

    This endpoint is hit by the user's browser after Google redirects back, so it
    is intentionally unauthenticated. Trust is established via the signed `state`
    parameter that carries the tenant id.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        error = request.query_params.get("error")
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        frontend_base = settings.FRONTEND_URL.rstrip("/") + "/integraciones"

        if error:
            return self._redirect_to_frontend(frontend_base, {"google": "error", "reason": error})

        if not code or not state:
            return self._redirect_to_frontend(
                frontend_base, {"google": "error", "reason": "missing_code_or_state"}
            )

        try:
            tenant_id = unsign_state(state)
        except ValueError as exc:
            return self._redirect_to_frontend(
                frontend_base, {"google": "error", "reason": str(exc)}
            )

        tenant = Tenant.objects.filter(id=tenant_id).first()
        if not tenant:
            return self._redirect_to_frontend(
                frontend_base, {"google": "error", "reason": "tenant_not_found"}
            )

        try:
            exchange = GoogleCalendarAdapter.exchange_code(code)
            save_credential_from_oauth(tenant=tenant, exchange=exchange)
        except Exception as exc:  # noqa: BLE001 — return all failures to the UI
            return self._redirect_to_frontend(
                frontend_base, {"google": "error", "reason": str(exc)[:200]}
            )

        return self._redirect_to_frontend(frontend_base, {"google": "connected"})

    @staticmethod
    def _redirect_to_frontend(base: str, params: dict) -> HttpResponseRedirect:
        return HttpResponseRedirect(f"{base}?{urlencode(params)}")


class GoogleCalendarSyncNowView(APIView):
    """Backfill / retry sync of all upcoming reservations to Google Calendar."""

    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.CORE.value
    required_permission_level = PermissionLevel.WRITE

    def post(self, request, tenant_id):
        from apps.booking.models import Reservation, ReservationStatus

        tenant = get_object_or_404(Tenant, id=tenant_id)
        credential = getattr(tenant, "google_calendar_credential", None)
        if credential is None or not credential.is_active:
            return Response(
                {"detail": "Google Calendar no esta conectado para este tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        adapter = GoogleCalendarAdapter(credential)
        reservations = (
            Reservation.all_objects.filter(tenant=tenant, check_out__gte=date.today())
            .exclude(status=ReservationStatus.CANCELLED)
            .select_related("property", "guest")
            .order_by("check_in")
        )

        synced = 0
        failed = 0
        errors: list[dict] = []
        for reservation in reservations:
            try:
                adapter.sync_reservation(reservation)
                synced += 1
            except Exception as exc:  # noqa: BLE001 — surface every error to the UI
                failed += 1
                errors.append({"reservation_id": str(reservation.id), "error": str(exc)[:200]})

        return Response(
            {
                "synced": synced,
                "failed": failed,
                "errors": errors,
                "last_sync_at": credential.last_sync_at.isoformat() if credential.last_sync_at else None,
                "last_sync_status": credential.last_sync_status,
            }
        )


class EmailTemplateViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Email/SMS message templates per tenant."""

    serializer_class = EmailTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.CORE.value
    lookup_url_kwarg = "template_id"

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs["tenant_id"])

    def get_queryset(self):
        return EmailTemplate.all_objects.filter(tenant=self.get_tenant())

    def get_serializer_class(self):
        if self.action == "create":
            return EmailTemplateCreateSerializer
        if self.action in {"partial_update", "update"}:
            return EmailTemplateUpdateSerializer
        return EmailTemplateSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant"] = self.get_tenant()
        return context

    def perform_create(self, serializer):
        serializer.save(tenant=self.get_tenant())

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)
