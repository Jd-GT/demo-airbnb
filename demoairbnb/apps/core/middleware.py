from __future__ import annotations

from uuid import UUID

from django.http import JsonResponse

from .models import Tenant
from .tenant_context import reset_current_tenant_id, set_current_tenant_id


class TenantResolutionMiddleware:
    """Resolves tenant by header/subdomain and sets tenant context for managers."""

    header_name = 'HTTP_X_TENANT_ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = self._resolve_tenant_id(request)
        tenant = None
        if tenant_id:
            tenant = Tenant.objects.filter(id=tenant_id, is_active=True).first()
            if tenant is None:
                return JsonResponse({'detail': 'Tenant not found.'}, status=404)

        request.tenant = tenant
        request.tenant_id = tenant.id if tenant else None
        token = set_current_tenant_id(request.tenant_id)
        try:
            response = self.get_response(request)
        finally:
            reset_current_tenant_id(token)
        return response

    def _resolve_tenant_id(self, request):
        tenant_header = request.META.get(self.header_name)
        if tenant_header:
            try:
                return UUID(tenant_header)
            except ValueError:
                return None

        host = request.get_host().split(':')[0]
        parts = host.split('.')
        if len(parts) > 2:
            subdomain = parts[0]
            tenant = (
                Tenant.objects.filter(subdomain=subdomain, is_active=True)
                .only('id')
                .first()
            )
            if tenant:
                return tenant.id

        return None
