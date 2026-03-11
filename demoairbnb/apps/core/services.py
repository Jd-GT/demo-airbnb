from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from .constants import SystemRole
from .models import Tenant, TenantRole, User, default_admin_permissions, default_read_permissions


@transaction.atomic
def seed_default_roles(tenant: Tenant) -> tuple[TenantRole, TenantRole]:
    admin_role, _ = TenantRole.all_objects.get_or_create(
        tenant=tenant,
        name="Admin Total",
        defaults={"permissions": default_admin_permissions(), "is_default": False},
    )
    readonly_role, _ = TenantRole.all_objects.get_or_create(
        tenant=tenant,
        name="Solo Lectura",
        defaults={"permissions": default_read_permissions(), "is_default": True},
    )
    return admin_role, readonly_role


@transaction.atomic
def create_tenant_with_owner(*, name: str, subdomain: str, owner_email: str, owner_password: str, owner_full_name: str, branding_config: dict | None = None, integration_config: dict | None = None) -> tuple[Tenant, User]:
    tenant = Tenant.objects.create(
        name=name,
        subdomain=subdomain,
        branding_config=branding_config or {},
        integration_config=integration_config or {},
    )

    admin_role, _ = seed_default_roles(tenant)

    owner = User.objects.create_user(
        email=owner_email,
        password=owner_password,
        full_name=owner_full_name,
        tenant=tenant,
        role=admin_role,
        system_role=SystemRole.OWNER.value,
        is_primary_owner=True,
    )
    return tenant, owner


@transaction.atomic
def create_tenant_user(*, tenant: Tenant, email: str, password: str, full_name: str, system_role: str = SystemRole.MEMBER.value, role: TenantRole | None = None) -> User:
    if system_role == SystemRole.MEMBER.value and role is None:
        role = TenantRole.all_objects.filter(tenant=tenant, is_default=True).first()

    if role and role.tenant_id != tenant.id:
        raise ValidationError({"role": "Role must belong to the same tenant."})

    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        tenant=tenant,
        role=role,
        system_role=system_role,
    )
    return user


@transaction.atomic
def update_tenant_user(*, user: User, data: dict):
    if user.is_primary_owner:
        if data.get("system_role") and data["system_role"] != SystemRole.OWNER.value:
            raise ValidationError({"system_role": "Primary owner cannot be downgraded."})
        if "is_active" in data and data["is_active"] is False:
            raise ValidationError({"is_active": "Primary owner cannot be deactivated."})

    for key, value in data.items():
        setattr(user, key, value)
    user.save()
    return user
