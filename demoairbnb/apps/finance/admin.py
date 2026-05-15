"""Finance admin: super-admin can review taxes, accounts, lines and payments."""

from __future__ import annotations

from django.contrib import admin

from .models import AnalyticAccount, AnalyticLine, Payment, Tax


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
