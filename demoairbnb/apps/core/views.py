from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
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
from .models import GoogleCalendarCredential, Tenant, TenantRole, User, EmailTemplate
from .permissions import TenantModulePermission
from .serializers import (
    IntegrationItemSerializer,
    PersonalizedTokenObtainPairSerializer,
    TenantCreateSerializer,
    TenantRoleSerializer,
    TenantSerializer,
    TenantUserCreateSerializer,
    TenantUserSerializer,
    TenantUserUpdateSerializer,
    EmailTemplateSerializer,
    EmailTemplateCreateSerializer,
    EmailTemplateUpdateSerializer,
)
from .services import normalize_integrations_config


class PersonalizedTokenObtainPairView(TokenObtainPairView):
    serializer_class = PersonalizedTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh_token") or request.data.get("refresh")

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                return Response(
                    {"detail": "Invalid refresh token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK,
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
