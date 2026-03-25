from __future__ import annotations

from rest_framework import permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.core.constants import ModuleKey, PermissionLevel
from apps.core.permissions import TenantModulePermission

from .serializers import FinanceAnalyticsQuerySerializer, FinanceAnalyticsSerializer
from .services import get_finance_analytics, resolve_year_month


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
