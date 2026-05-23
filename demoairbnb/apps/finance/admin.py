"""Finance admin registrations."""

from __future__ import annotations

from django.contrib import admin

from .models import (
    AnalyticAccount,
    AnalyticLine,
    Payment,
    PropertyProfitabilityReport,
    Tax,
    Voucher,
)


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'value', 'type', 'is_active')
    list_filter = ('type', 'is_active', 'tenant')
    search_fields = ('name',)


@admin.register(AnalyticAccount)
class AnalyticAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'property', 'is_active', 'balance_display')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name',)

    @admin.display(description='Saldo')
    def balance_display(self, obj):
        return obj.get_balance()


@admin.register(AnalyticLine)
class AnalyticLineAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'account',
        'amount',
        'category',
        'description',
        'tenant',
    )
    list_filter = ('category', 'tenant')
    search_fields = ('description',)
    date_hierarchy = 'date'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'amount',
        'method',
        'type',
        'reservation',
        'reference',
        'recorded_by',
    )
    list_filter = ('method', 'type', 'tenant')
    search_fields = ('reference', 'notes')
    date_hierarchy = 'date'


@admin.register(PropertyProfitabilityReport)
class PropertyProfitabilityReportAdmin(admin.ModelAdmin):
    list_display = (
        'property',
        'year',
        'month',
        'gross_revenue',
        'net_profit',
        'occupancy_rate',
    )
    list_filter = ('tenant', 'year', 'month', 'property')
    search_fields = ('property__name',)
    readonly_fields = (
        'created_at',
        'updated_at',
        'net_revenue',
        'total_expenses',
        'net_profit',
    )


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = (
        'reference_number',
        'voucher_type',
        'status',
        'guest_name',
        'property_name',
        'net_amount',
        'issue_date',
    )
    list_filter = ('voucher_type', 'status', 'tenant', 'issue_date')
    search_fields = ('reference_number', 'guest_name', 'guest_email', 'property_name')
    readonly_fields = ('reference_number', 'issue_date', 'created_at', 'updated_at')
