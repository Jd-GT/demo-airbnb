from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .constants import (
    PermissionLevel,
    SystemRole,
    modules_default_permissions,
    validate_permissions_map,
)
from .managers import TenantAwareManager, UserManager


class TimeStampedUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Tenant(TimeStampedUUIDModel):
    name = models.CharField(max_length=160)
    subdomain = models.SlugField(max_length=80, unique=True)
    branding_config = models.JSONField(default=dict, blank=True)
    integration_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class TenantAwareModel(TimeStampedUUIDModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    objects = TenantAwareManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class TenantRole(TenantAwareModel):
    name = models.CharField(max_length=120)
    permissions = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='tenant_role_unique_name'
            ),
            models.UniqueConstraint(
                fields=['tenant'],
                condition=Q(is_default=True),
                name='tenant_single_default_role',
            ),
        ]

    def clean(self):
        try:
            self.permissions = validate_permissions_map(self.permissions)
        except ValueError as exc:
            raise ValidationError({'permissions': str(exc)}) from exc

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.tenant.name} - {self.name}'


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=160)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
    )
    role = models.ForeignKey(
        TenantRole,
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True,
    )
    system_role = models.CharField(
        max_length=12,
        choices=[(role.value, role.value) for role in SystemRole],
        default=SystemRole.MEMBER.value,
    )
    is_primary_owner = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ['email']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant'],
                condition=Q(is_primary_owner=True),
                name='single_primary_owner_per_tenant',
            )
        ]

    def clean(self):
        if (
            self.system_role == SystemRole.OWNER.value
            and not self.tenant
            and not self.is_superuser
        ):
            raise ValidationError({'tenant': 'Owner users must belong to a tenant.'})

        if self.system_role == SystemRole.MEMBER.value:
            if self.tenant and not self.role:
                raise ValidationError({'role': 'Member users must have a tenant role.'})
            if self.tenant and self.role and self.role.tenant_id != self.tenant_id:
                raise ValidationError({'role': 'Role must belong to the same tenant.'})

        if self.system_role != SystemRole.MEMBER.value:
            self.role = None

        if self.is_primary_owner:
            self.system_role = SystemRole.OWNER.value
            self.is_active = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_owner(self) -> bool:
        return self.system_role == SystemRole.OWNER.value

    def can_access_module(self, module: str, required_level: PermissionLevel) -> bool:
        if self.is_superuser or self.is_owner:
            return True

        if not self.role:
            return False

        granted_level = self.role.permissions.get(module, PermissionLevel.NONE.value)
        hierarchy = {
            PermissionLevel.NONE.value: 0,
            PermissionLevel.READ.value: 1,
            PermissionLevel.WRITE.value: 2,
            PermissionLevel.ADMIN.value: 3,
        }
        return hierarchy.get(granted_level, 0) >= hierarchy[required_level.value]

    def __str__(self) -> str:
        return self.email


def default_admin_permissions() -> dict[str, str]:
    return modules_default_permissions(PermissionLevel.ADMIN)


def default_read_permissions() -> dict[str, str]:
    return modules_default_permissions(PermissionLevel.READ)
