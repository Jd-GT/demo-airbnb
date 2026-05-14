from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.core.constants import ModuleKey, PermissionLevel
from apps.core.models import Tenant
from apps.core.permissions import TenantModulePermission
from apps.core.pdf_service import generate_property_report_pdf
from apps.inventory.models import Property

from .models import PropertyProfitabilityReport, Voucher
from .serializers import (
    FinanceAnalyticsQuerySerializer,
    FinanceAnalyticsSerializer,
    PropertyProfitabilityReportSerializer,
    PropertyProfitabilityReportCreateSerializer,
    VoucherSerializer,
    VoucherCreateSerializer,
)
from .services import (
    get_finance_analytics,
    resolve_year_month,
    calculate_property_profitability,
)


class FinanceAnalyticsView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.FINANCE.value
    required_permission_level = PermissionLevel.READ
    serializer_class = FinanceAnalyticsSerializer
    query_serializer_class = FinanceAnalyticsQuerySerializer

    def get(self, request, tenant_id):
        query_serializer = self.query_serializer_class(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        year, month = resolve_year_month(request.query_params)
        serializer = self.get_serializer(
            get_finance_analytics(tenant_id=tenant_id, year=year, month=month)
        )
        return Response(serializer.data)


class PropertyProfitabilityReportViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Property Profit & Loss reports."""

    serializer_class = PropertyProfitabilityReportSerializer
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.FINANCE.value
    lookup_url_kwarg = "report_id"

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs["tenant_id"])

    def get_queryset(self):
        return PropertyProfitabilityReport.all_objects.filter(
            tenant=self.get_tenant()
        ).select_related("property")

    def get_serializer_class(self):
        if self.action == "create":
            return PropertyProfitabilityReportCreateSerializer
        return PropertyProfitabilityReportSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant"] = self.get_tenant()
        return context

    @action(detail=False, methods=["post"])
    def calculate_for_property(self, request, tenant_id, **kwargs):
        """Calculate P&L report for a specific property."""
        tenant = self.get_tenant()
        property_id = request.data.get("property_id")
        year = request.data.get("year")
        month = request.data.get("month")

        if not all([property_id, year, month]):
            return Response(
                {"error": "property_id, year, and month are required"},
                status=400,
            )

        property_obj = get_object_or_404(
            Property, id=property_id, tenant=tenant
        )

        report = calculate_property_profitability(
            property_obj,
            year=year,
            month=month,
            **request.data.get("expenses", {}),
        )

        serializer = PropertyProfitabilityReportSerializer(report)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request, tenant_id, report_id):
        """Download property profitability report as PDF."""
        report = self.get_object()
        
        try:
            from datetime import datetime
            now = datetime.now()
            month_names = [
                "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
            ]
            month_str = month_names[now.month - 1]
            period = f"{month_str} {now.year}"
            
            # Generate PDF report directly
            pdf_bytes = generate_property_report_pdf(
                property_name=report.property.name,
                period=period,
                total_revenue=report.total_revenue,
                occupancy_rate=report.occupancy_rate,
                nights_booked=report.nights_booked,
                num_reservations=report.num_reservations,
                avg_daily_rate=report.avg_daily_rate,
                operating_expenses=getattr(report, 'expenses', None),
                net_profit=report.net_profit,
            )
            
            # Return PDF response
            response = Response(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="report-{report.property.name.replace(" ", "_")}.pdf"'
            return response
        except Exception as e:
            return Response(
                {"error": f"Error generating PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VoucherViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Vouchers/Receipts for guest stays or transactions."""

    serializer_class = VoucherSerializer
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.FINANCE.value
    lookup_url_kwarg = "voucher_id"

    def get_tenant(self):
        return get_object_or_404(Tenant, id=self.kwargs["tenant_id"])

    def get_queryset(self):
        return Voucher.all_objects.filter(tenant=self.get_tenant())

    def get_serializer_class(self):
        if self.action == "create":
            return VoucherCreateSerializer
        return VoucherSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tenant"] = self.get_tenant()
        return context

    @action(detail=True, methods=["get"])
    def download_pdf(self, request, tenant_id, voucher_id):
        """Download voucher as PDF."""
        tenant = self.get_tenant()
        voucher = get_object_or_404(
            Voucher, id=voucher_id, tenant=tenant
        )

        if voucher.pdf_file:
            return Response(
                {
                    "message": "PDF disponible",
                    "pdf_url": voucher.pdf_file.url,
                    "reference_number": voucher.reference_number,
                },
                status=200,
            )

        return Response(
            {"error": "PDF no disponible. El voucher aún no ha sido procesado."},
            status=404,
        )
