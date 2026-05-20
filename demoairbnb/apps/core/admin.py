from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.urls import reverse
from django.utils.html import format_html

from .integrations import GoogleCalendarCredential
from .models import (
    EmailTemplate,
    InvitationCode,
    InvitationCodePurpose,
    Tenant,
    TenantRole,
    User,
)
from .services import issue_create_tenant_code

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'subdomain',
        'is_active',
        'users_count',
        'created_at',
    )
    list_filter = ('is_active',)
    search_fields = ('name', 'subdomain')
    actions = ['activate_tenants', 'deactivate_tenants']
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('name', 'subdomain', 'is_active')}),
        (
            'Branding & Integraciones',
            {
                'classes': ('collapse',),
                'fields': ('branding_config', 'integration_config'),
            },
        ),
        ('Auditoría', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Usuarios')
    def users_count(self, obj):
        return obj.users.count()

    @admin.action(description='Activar tenants seleccionados')
    def activate_tenants(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} tenant(s) activado(s).', messages.SUCCESS)

    @admin.action(description='Desactivar tenants (bloquea login y signups)')
    def deactivate_tenants(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} tenant(s) desactivado(s). Los usuarios no podrán entrar.',
            messages.WARNING,
        )


@admin.register(TenantRole)
class TenantRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_default')
    list_filter = ('tenant', 'is_default')
    search_fields = ('name',)


@admin.register(InvitationCode)
class InvitationCodeAdmin(admin.ModelAdmin):
    """Super-admin manages CREATE_TENANT codes here.

    Tenant owners manage their JOIN_TENANT codes from the frontend
    /settings page (REST API), but they appear here too for super-admin
    visibility / troubleshooting.
    """

    list_display = (
        'code',
        'purpose',
        'tenant_link',
        'uses_summary',
        'is_active',
        'is_expired_display',
        'expires_at',
        'created_at',
        'created_by',
    )
    list_filter = ('purpose', 'is_active', 'tenant')
    search_fields = ('code', 'notes', 'tenant__name', 'tenant__subdomain')
    readonly_fields = (
        'code',
        'uses_count',
        'is_expired_display',
        'is_exhausted_display',
        'created_at',
        'updated_at',
        'created_by',
    )
    actions = [
        'create_tenant_code_action',
        'deactivate_codes',
        'reactivate_codes',
    ]

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'code',
                    'purpose',
                    'tenant',
                    'role',
                    'is_active',
                )
            },
        ),
        (
            'Uso y vigencia',
            {
                'fields': (
                    'max_uses',
                    'uses_count',
                    'expires_at',
                    'is_expired_display',
                    'is_exhausted_display',
                )
            },
        ),
        ('Notas internas', {'fields': ('notes',)}),
        (
            'Auditoría',
            {'fields': ('created_by', 'created_at', 'updated_at')},
        ),
    )

    @admin.display(description='Empresa', ordering='tenant')
    def tenant_link(self, obj):
        if not obj.tenant_id:
            return format_html(
                '<span style="color:#16a34a;font-weight:600">[NUEVO TENANT]</span>'
            )
        url = reverse('admin:core_tenant_change', args=[obj.tenant_id])
        return format_html('<a href="{}">{}</a>', url, obj.tenant.subdomain)

    @admin.display(description='Usos')
    def uses_summary(self, obj):
        return f'{obj.uses_count} / {obj.max_uses}'

    @admin.display(boolean=True, description='Expirado')
    def is_expired_display(self, obj):
        return obj.is_expired

    @admin.display(boolean=True, description='Agotado')
    def is_exhausted_display(self, obj):
        return obj.is_exhausted

    @admin.action(description='Generar código nuevo CREATE_TENANT (1 uso)')
    def create_tenant_code_action(self, request, queryset):
        invite = issue_create_tenant_code(
            created_by=request.user,
            notes='Generado desde Django Admin',
            max_uses=1,
        )
        self.message_user(
            request,
            f'Código generado: {invite.code} (válido para crear 1 nueva empresa).',
            messages.SUCCESS,
        )

    @admin.action(description='Desactivar códigos seleccionados')
    def deactivate_codes(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} código(s) desactivado(s).')

    @admin.action(description='Reactivar códigos seleccionados')
    def reactivate_codes(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} código(s) reactivado(s).')

    def get_changeform_initial_data(self, request):
        return {'purpose': InvitationCodePurpose.CREATE_TENANT.value, 'max_uses': 1}


@admin.register(GoogleCalendarCredential)
class GoogleCalendarCredentialAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'calendar_id', 'is_active',
        'last_sync_status', 'last_sync_at',
    )
    list_filter = ('is_active', 'last_sync_status')
    readonly_fields = ('refresh_token_encrypted', 'last_sync_at')


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        'email',
        'full_name',
        'tenant',
        'system_role',
        'is_active',
        'is_staff',
    )
    list_filter = ('system_role', 'is_active', 'is_staff', 'is_superuser', 'tenant')
    ordering = ('email',)
    search_fields = ('email', 'full_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            'Personal info',
            {
                'fields': (
                    'full_name',
                    'tenant',
                    'role',
                    'system_role',
                    'is_primary_owner',
                )
            },
        ),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'full_name',
                    'password1',
                    'password2',
                    'is_staff',
                    'is_superuser',
                ),
            },
        ),
    )


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "template_type", "tenant", "is_active", "is_default", "created_at")
    list_filter = ("template_type", "is_active", "is_default", "tenant")
    search_fields = ("name", "subject", "body")
    fieldsets = (
        (None, {"fields": ("tenant", "name", "template_type")}),
        ("Content", {"fields": ("subject", "body")}),
        (
            "Settings",
            {"fields": ("is_active", "is_default", "variables_used")},
        ),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")
