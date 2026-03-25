from __future__ import annotations

from rest_framework import serializers


class FinanceAnalyticsQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)


class MonthlyRevenuePointSerializer(serializers.Serializer):
    month_index = serializers.IntegerField()
    month = serializers.CharField()
    ingresos = serializers.DecimalField(max_digits=14, decimal_places=2)


class RevenueByPropertySerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    name = serializers.CharField()
    ingresos = serializers.DecimalField(max_digits=14, decimal_places=2)


class FinanceAnalyticsSerializer(serializers.Serializer):
    monthly_revenue_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    annual_revenue_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    monthly_revenue_series = MonthlyRevenuePointSerializer(many=True)
    revenue_by_property = RevenueByPropertySerializer(many=True)
