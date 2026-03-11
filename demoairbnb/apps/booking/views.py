from __future__ import annotations

from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

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
        return Reservation.all_objects.filter(tenant_id=self.kwargs["tenant_id"]).select_related(
            "property", "guest", "agent"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationCreateSerializer
        return ReservationSerializer


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
