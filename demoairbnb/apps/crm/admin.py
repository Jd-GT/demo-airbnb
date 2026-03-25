from django.contrib import admin

from .models import Contact, Lead


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'type', 'email', 'phone')
    list_filter = ('tenant', 'type')
    search_fields = ('name', 'email', 'phone')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tenant',
        'contact',
        'stage',
        'expected_revenue',
        'created_at',
    )
    list_filter = ('tenant', 'stage')
    search_fields = ('contact__name', 'notes')
