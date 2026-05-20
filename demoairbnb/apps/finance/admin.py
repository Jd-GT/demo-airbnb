"""Finance admin registrations."""

from django.contrib import admin

from .models import PropertyProfitabilityReport, Voucher


@admin.register(PropertyProfitabilityReport)
class PropertyProfitabilityReportAdmin(admin.ModelAdmin):
    list_display = (
        "property",
        "year",
        "month",
        "gross_revenue",
        "net_profit",
        "occupancy_rate",
    )
    list_filter = ("tenant", "year", "month", "property")
    search_fields = ("property__name",)
    fieldsets = (
        (None, {"fields": ("tenant", "property", "year", "month")}),
        (
            "Revenue",
            {
                "fields": (
                    "gross_revenue",
                    "commissions",
                    "net_revenue",
                )
            },
        ),
        (
            "Expenses",
            {
                "fields": (
                    "cleaning_costs",
                    "maintenance_costs",
                    "utilities_costs",
                    "platform_fees",
                    "property_management_fee",
                    "other_expenses",
                    "total_expenses",
                )
            },
        ),
        (
            "Results",
            {
                "fields": (
                    "net_profit",
                    "profit_margin",
                )
            },
        ),
        (
            "Metrics",
            {
                "fields": (
                    "occupied_nights",
                    "total_nights",
                    "occupancy_rate",
                    "avg_daily_rate",
                    "revenue_per_available_night",
                )
            },
        ),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "net_revenue", "total_expenses", "net_profit")


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number",
        "voucher_type",
        "status",
        "guest_name",
        "property_name",
        "net_amount",
        "issue_date",
    )
    list_filter = ("voucher_type", "status", "tenant", "issue_date")
    search_fields = ("reference_number", "guest_name", "guest_email", "property_name")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "tenant",
                    "reference_number",
                    "voucher_type",
                    "status",
                )
            },
        ),
        (
            "Guest & Property",
            {
                "fields": (
                    "guest_name",
                    "guest_email",
                    "property_name",
                )
            },
        ),
        (
            "Financial",
            {
                "fields": (
                    "gross_amount",
                    "tax_amount",
                    "net_amount",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "issue_date",
                    "check_in",
                    "check_out",
                )
            },
        ),
        (
            "Additional",
            {
                "fields": (
                    "pdf_file",
                    "notes",
                )
            },
        ),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("reference_number", "issue_date", "created_at", "updated_at")
