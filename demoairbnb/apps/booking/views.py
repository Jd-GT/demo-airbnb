from __future__ import annotations

from datetime import date

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import ValidationError

from apps.core.constants import ModuleKey, PermissionLevel
from apps.core.permissions import TenantModulePermission

from .models import Reservation
from .serializers import AvailabilitySerializer, QuoteSerializer, ReservationCreateSerializer, ReservationSerializer
from .services import calculate_quote, check_availability


class TenantScopedBookingMixin:
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.BOOKING.value

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant_id"] = self.kwargs["tenant_id"]
        return context


class ReservationViewSet(
    TenantScopedBookingMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    lookup_url_kwarg = "reservation_id"

    def get_queryset(self):
        queryset = Reservation.all_objects.filter(tenant_id=self.kwargs["tenant_id"]).select_related(
            "property", "guest", "agent"
        )
        from_raw = self.request.query_params.get("from")
        to_raw = self.request.query_params.get("to")

        from_date = self._parse_date(from_raw, "from") if from_raw else None
        to_date = self._parse_date(to_raw, "to") if to_raw else None

        if from_date:
            queryset = queryset.filter(check_out__gt=from_date)
        if to_date:
            queryset = queryset.filter(check_in__lt=to_date)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationCreateSerializer
        return ReservationSerializer

    def _parse_date(self, raw_value: str, field_name: str) -> date:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise ValidationError({field_name: "Expected ISO date YYYY-MM-DD."}) from exc


class AvailabilityCheckView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.BOOKING.value
    required_permission_level = PermissionLevel.READ
    serializer_class = AvailabilitySerializer

    def post(self, request, tenant_id):
        serializer = self.get_serializer(data=request.data, context={"tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)

        available, conflicts = check_availability(
            tenant_id=tenant_id,
            property_id=serializer.validated_data["property_obj"].id,
            check_in=serializer.validated_data["check_in"],
            check_out=serializer.validated_data["check_out"],
        )
        return Response(
            {
                "available": available,
                "conflicting_reservation_ids": conflicts,
                "property_id": str(serializer.validated_data["property_obj"].id),
            },
            status=status.HTTP_200_OK,
        )


class QuoteView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.BOOKING.value
    required_permission_level = PermissionLevel.READ
    serializer_class = QuoteSerializer

    def post(self, request, tenant_id):
        serializer = self.get_serializer(data=request.data, context={"tenant_id": tenant_id})
        serializer.is_valid(raise_exception=True)

        quote = calculate_quote(
            property_obj=serializer.validated_data["property_obj"],
            check_in=serializer.validated_data["check_in"],
            check_out=serializer.validated_data["check_out"],
        )

        return Response(
            {
                "property_id": str(serializer.validated_data["property_obj"].id),
                "check_in": serializer.validated_data["check_in"],
                "check_out": serializer.validated_data["check_out"],
                "nights": quote.nights,
                "nightly_rate": str(quote.nightly_rate),
                "subtotal_amount": str(quote.subtotal_amount),
                "cleaning_fee": str(quote.cleaning_fee),
                "total_amount": str(quote.total_amount),
            },
            status=status.HTTP_200_OK,
        )
