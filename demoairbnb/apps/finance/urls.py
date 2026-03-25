from django.urls import path

from .views import FinanceAnalyticsView

urlpatterns = [
    path(
        'tenants/<uuid:tenant_id>/finance/analytics/',
        FinanceAnalyticsView.as_view(),
        name='finance-analytics',
    ),
]
