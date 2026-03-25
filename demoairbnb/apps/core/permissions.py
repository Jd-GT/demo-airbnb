from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .constants import PermissionLevel


def _required_level_for_request(request_method: str) -> PermissionLevel:
    if request_method in SAFE_METHODS:
        return PermissionLevel.READ
    return PermissionLevel.WRITE


class TenantModulePermission(BasePermission):
    """Tenant membership + module level RBAC enforcement."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        tenant_id = view.kwargs.get("tenant_id")
        if tenant_id and not user.is_superuser:
            if not user.tenant_id or str(user.tenant_id) != str(tenant_id):
                return False

        required_level = getattr(view, "required_permission_level", _required_level_for_request(request.method))
        module = getattr(view, "permission_module", None)
        if module is None:
            return True
        return user.can_access_module(module=module, required_level=required_level)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True

        obj_tenant_id = getattr(obj, "tenant_id", None)
        if obj_tenant_id and user.tenant_id and str(obj_tenant_id) != str(user.tenant_id):
            return False

        required_level = getattr(view, "required_permission_level", _required_level_for_request(request.method))
        module = getattr(view, "permission_module", None)
        if module is None:
            return True
        return user.can_access_module(module=module, required_level=required_level)
