from __future__ import annotations

from datetime import date

from django.http import HttpResponse
from rest_framework import mixins, permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.core.constants import ModuleKey, PermissionLevel
from apps.core.permissions import TenantModulePermission

from .models import AnalyticAccount, AnalyticLine, Payment, Tax
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
    TaxSerializer,
)
from .services import (
    build_occupancy_xlsx,
    build_payments_xlsx,
    build_pnl_xlsx,
    delete_payment,
    get_finance_analytics,
    get_profit_and_loss,
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
