from django.urls import path

from .views import (
    FinanceAnalyticsView,
    PropertyProfitabilityReportViewSet,
    VoucherViewSet,
)


analytics_view = FinanceAnalyticsView.as_view()

profitability_list = PropertyProfitabilityReportViewSet.as_view({"get": "list", "post": "create"})
profitability_detail = PropertyProfitabilityReportViewSet.as_view({"get": "retrieve"})
profitability_calculate = PropertyProfitabilityReportViewSet.as_view({"post": "calculate_for_property"})

voucher_list = VoucherViewSet.as_view({"get": "list", "post": "create"})
voucher_detail = VoucherViewSet.as_view({"get": "retrieve"})
voucher_download = VoucherViewSet.as_view({"get": "download_pdf"})

urlpatterns = [
    path(
        "tenants/<uuid:tenant_id>/finance/analytics/",
        analytics_view,
        name="finance-analytics",
    ),
    path(
        "tenants/<uuid:tenant_id>/finance/profitability/",
        profitability_list,
        name="profitability-list",
    ),
    path(
        "tenants/<uuid:tenant_id>/finance/profitability/<uuid:report_id>/",
        profitability_detail,
        name="profitability-detail",
    ),
    path(
        "tenants/<uuid:tenant_id>/finance/profitability/calculate/",
        profitability_calculate,
        name="profitability-calculate",
    ),
    path(
        "tenants/<uuid:tenant_id>/finance/vouchers/",
        voucher_list,
        name="voucher-list",
    ),
    path(
        "tenants/<uuid:tenant_id>/finance/vouchers/<uuid:voucher_id>/",
        voucher_detail,
        name="voucher-detail",
    ),
    path(
        "tenants/<uuid:tenant_id>/finance/vouchers/<uuid:voucher_id>/download/",
        voucher_download,
        name="voucher-download",
    ),
]
