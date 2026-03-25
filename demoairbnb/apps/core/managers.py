from __future__ import annotations

from django.contrib.auth.base_user import BaseUserManager
from django.db import models

from .tenant_context import get_current_tenant_id


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError('The email must be set')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email=email, password=password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('system_role', 'OWNER')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email=email, password=password, **extra_fields)


class TenantAwareQuerySet(models.QuerySet):
    def for_tenant(self, tenant_id):
        return self.filter(tenant_id=tenant_id)


class TenantAwareManager(models.Manager.from_queryset(TenantAwareQuerySet)):
    """Filters by active tenant context when available."""

    def get_queryset(self):
        queryset = super().get_queryset()
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            return queryset
        return queryset.filter(tenant_id=tenant_id)
