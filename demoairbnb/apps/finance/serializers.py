from __future__ import annotations

from rest_framework import serializers

from .models import PropertyProfitabilityReport, Voucher


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


class PropertyProfitabilityReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyProfitabilityReport
        fields = [
            "id",
            "property",
            "year",
            "month",
            "gross_revenue",
            "commissions",
            "net_revenue",
            "cleaning_costs",
            "maintenance_costs",
            "utilities_costs",
            "platform_fees",
            "property_management_fee",
            "other_expenses",
            "total_expenses",
            "net_profit",
            "profit_margin",
            "occupied_nights",
            "total_nights",
            "occupancy_rate",
            "avg_daily_rate",
            "revenue_per_available_night",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyProfitabilityReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyProfitabilityReport
        fields = [
            "property",
            "year",
            "month",
            "gross_revenue",
            "commissions",
            "cleaning_costs",
            "maintenance_costs",
            "utilities_costs",
            "platform_fees",
            "property_management_fee",
            "other_expenses",
            "occupied_nights",
            "total_nights",
        ]

    def create(self, validated_data):
        tenant = self.context["tenant"]
        report = PropertyProfitabilityReport(tenant=tenant, **validated_data)
        report.calculate_metrics()
        report.save()
        return report


class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = [
            "id",
            "reference_number",
            "voucher_type",
            "status",
            "guest_name",
            "guest_email",
            "property_name",
            "gross_amount",
            "tax_amount",
            "net_amount",
            "issue_date",
            "check_in",
            "check_out",
            "pdf_file",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reference_number", "issue_date", "created_at", "updated_at"]


class VoucherCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = [
            "voucher_type",
            "guest_name",
            "guest_email",
            "property_name",
            "gross_amount",
            "tax_amount",
            "check_in",
            "check_out",
            "notes",
        ]

    def create(self, validated_data):
        tenant = self.context["tenant"]
        voucher = Voucher(tenant=tenant, **validated_data)
        voucher.net_amount = voucher.gross_amount - voucher.tax_amount
        voucher.save()
        return voucher

