from __future__ import annotations

from datetime import date

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.core.constants import ModuleKey, PermissionLevel
from apps.core.models import Tenant
from apps.core.permissions import TenantModulePermission
from apps.core.pdf_service import generate_property_report_pdf
from apps.inventory.models import Property

from .models import AnalyticAccount, AnalyticLine, Payment, PropertyProfitabilityReport, Tax, Voucher
from .serializers import (
    AnalyticAccountSerializer,
    AnalyticLineSerializer,
    ExpenseCreateSerializer,
    FinanceAnalyticsQuerySerializer,
    FinanceAnalyticsSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
    ProfitAndLossQuerySerializer,
    ProfitAndLossSerializer,
    PropertyProfitabilityReportCreateSerializer,
    PropertyProfitabilityReportSerializer,
    TaxSerializer,
    VoucherCreateSerializer,
    VoucherSerializer,
)
from .services import (
    build_occupancy_xlsx,
    build_payments_xlsx,
    build_pnl_xlsx,
    delete_payment,
    get_finance_analytics,
    get_profit_and_loss,
    calculate_property_profitability,
    resolve_year_month,
)


class TenantScopedFinanceMixin:
    permission_classes = [permissions.IsAuthenticated, TenantModulePermission]
    permission_module = ModuleKey.FINANCE.value

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['tenant_id'] = self.kwargs['tenant_id']
        return context


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

class TaxViewSet(
    TenantScopedFinanceMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TaxSerializer
    lookup_url_kwarg = 'tax_id'

    def get_queryset(self):
        return Tax.all_objects.filter(tenant_id=self.kwargs['tenant_id'])

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.kwargs['tenant_id'])


class AnalyticAccountViewSet(
    TenantScopedFinanceMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AnalyticAccountSerializer
    lookup_url_kwarg = 'account_id'

    def get_queryset(self):
        return AnalyticAccount.all_objects.filter(
            tenant_id=self.kwargs['tenant_id']
        ).select_related('property')

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.kwargs['tenant_id'])


class AnalyticLineListView(TenantScopedFinanceMixin, GenericAPIView):
    """Read-only list of analytic lines, optionally filtered by account/date."""

    serializer_class = AnalyticLineSerializer

    def get(self, request, tenant_id):
        qs = AnalyticLine.all_objects.filter(tenant_id=tenant_id).select_related('account')
        account_id = request.query_params.get('account_id')
        from_raw = request.query_params.get('from')
        to_raw = request.query_params.get('to')
        if account_id:
            qs = qs.filter(account_id=account_id)
        if from_raw:
            try:
                qs = qs.filter(date__gte=date.fromisoformat(from_raw))
            except ValueError as exc:
                raise ValidationError({'from': 'Expected ISO date YYYY-MM-DD.'}) from exc
        if to_raw:
            try:
                qs = qs.filter(date__lte=date.fromisoformat(to_raw))
            except ValueError as exc:
                raise ValidationError({'to': 'Expected ISO date YYYY-MM-DD.'}) from exc
        return Response(self.get_serializer(qs, many=True).data)


class ExpenseCreateView(TenantScopedFinanceMixin, GenericAPIView):
    """Manual expense entry creating a negative AnalyticLine."""

    serializer_class = ExpenseCreateSerializer

    def post(self, request, tenant_id):
        serializer = self.get_serializer(
            data=request.data,
            context={'tenant_id': tenant_id, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(serializer.to_representation(instance), status=201)


class PaymentViewSet(
    TenantScopedFinanceMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    lookup_url_kwarg = 'payment_id'

    def get_queryset(self):
        qs = Payment.all_objects.filter(
            tenant_id=self.kwargs['tenant_id']
        ).select_related('reservation__guest', 'reservation__property')
        reservation_id = self.request.query_params.get('reservation_id')
        if reservation_id:
            qs = qs.filter(reservation_id=reservation_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer

    def perform_destroy(self, instance):
        delete_payment(instance)


class ProfitAndLossView(TenantScopedFinanceMixin, GenericAPIView):
    serializer_class = ProfitAndLossSerializer
    required_permission_level = PermissionLevel.READ

    def get(self, request, tenant_id):
        query = ProfitAndLossQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        account = None
        if query.validated_data.get('account_id'):
            account = AnalyticAccount.all_objects.filter(
                tenant_id=tenant_id, id=query.validated_data['account_id']
            ).first()
            if not account:
                raise ValidationError({'account_id': 'Account not found for tenant.'})
        result = get_profit_and_loss(
            tenant_id=tenant_id,
            account=account,
            from_date=query.validated_data.get('from_date'),
            to_date=query.validated_data.get('to_date'),
        )
        return Response(result)


# ---------- Excel exports ----------

class XlsxExportBase(TenantScopedFinanceMixin, GenericAPIView):
    required_permission_level = PermissionLevel.READ
    filename_prefix = 'export'
    serializer_class = None  # not used, drf-spectacular fallback

    def _xlsx_response(self, data: bytes, filename: str) -> HttpResponse:
        response = HttpResponse(
            data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class PnLXlsxView(XlsxExportBase):
    def get(self, request, tenant_id):
        year, _ = resolve_year_month(request.query_params)
        data = build_pnl_xlsx(tenant_id=tenant_id, year=year)
        return self._xlsx_response(data, f'pnl_{year}.xlsx')


class OccupancyXlsxView(XlsxExportBase):
    def get(self, request, tenant_id):
        year, _ = resolve_year_month(request.query_params)
        data = build_occupancy_xlsx(tenant_id=tenant_id, year=year)
        return self._xlsx_response(data, f'occupancy_{year}.xlsx')


class PaymentsXlsxView(XlsxExportBase):
    def get(self, request, tenant_id):
        from_raw = request.query_params.get('from')
        to_raw = request.query_params.get('to')
        from_date = date.fromisoformat(from_raw) if from_raw else None
        to_date = date.fromisoformat(to_raw) if to_raw else None
        data = build_payments_xlsx(tenant_id=tenant_id, from_date=from_date, to_date=to_date)
        return self._xlsx_response(data, 'payments.xlsx')


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

            pdf_bytes = generate_property_report_pdf(
                property_name=report.property.name,
                period=period,
                total_revenue=report.gross_revenue,
                occupancy_rate=float(report.occupancy_rate),
                nights_booked=report.occupied_nights,
                num_reservations=0,
                avg_daily_rate=report.avg_daily_rate,
                operating_expenses=report.total_expenses,
                net_profit=report.net_profit,
            )
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
