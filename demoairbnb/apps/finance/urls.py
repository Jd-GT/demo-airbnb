"""URL routes for the finance app."""

from django.urls import path

from .views import (
    AnalyticAccountViewSet,
    AnalyticLineListView,
    ExpenseCreateView,
    FinanceAnalyticsView,
    OccupancyXlsxView,
    PaymentsXlsxView,
    PaymentViewSet,
    PnLXlsxView,
    ProfitAndLossView,
    TaxViewSet,
)

tax_list = TaxViewSet.as_view({'get': 'list', 'post': 'create'})
tax_detail = TaxViewSet.as_view(
    {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}
)

account_list = AnalyticAccountViewSet.as_view({'get': 'list', 'post': 'create'})
account_detail = AnalyticAccountViewSet.as_view(
    {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}
)

payment_list = PaymentViewSet.as_view({'get': 'list', 'post': 'create'})
payment_detail = PaymentViewSet.as_view(
    {'get': 'retrieve', 'delete': 'destroy'}
)

urlpatterns = [
    path(
        'tenants/<uuid:tenant_id>/finance/analytics/',
        FinanceAnalyticsView.as_view(),
        name='finance-analytics',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/taxes/',
        tax_list,
        name='tax-list',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/taxes/<uuid:tax_id>/',
        tax_detail,
        name='tax-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/cost-centers/',
        account_list,
        name='cost-center-list',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/cost-centers/<uuid:account_id>/',
        account_detail,
        name='cost-center-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/analytic-lines/',
        AnalyticLineListView.as_view(),
        name='analytic-lines',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/expenses/',
        ExpenseCreateView.as_view(),
        name='expense-create',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/payments/',
        payment_list,
        name='payment-list',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/payments/<uuid:payment_id>/',
        payment_detail,
        name='payment-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/profit-and-loss/',
        ProfitAndLossView.as_view(),
        name='profit-and-loss',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/reports/pnl.xlsx',
        PnLXlsxView.as_view(),
        name='pnl-xlsx',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/reports/occupancy.xlsx',
        OccupancyXlsxView.as_view(),
        name='occupancy-xlsx',
    ),
    path(
        'tenants/<uuid:tenant_id>/finance/reports/payments.xlsx',
        PaymentsXlsxView.as_view(),
        name='payments-xlsx',
    ),
]
