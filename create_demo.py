#!/usr/bin/env python
import os
import sys
import django

sys.path.insert(0, '/app/demoairbnb')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demoairbnb.settings')
django.setup()

from apps.core.models import Tenant, TenantRole, User
from apps.core.constants import SystemRole, PermissionLevel, modules_default_permissions

tenant, _ = Tenant.objects.get_or_create(
    subdomain='demo',
    defaults={'name': 'Demo Tenant', 'is_active': True}
)

role, _ = TenantRole.objects.get_or_create(
    tenant=tenant,
    name='Admin',
    defaults={
        'permissions': modules_default_permissions(PermissionLevel.ADMIN),
        'is_default': True
    }
)

user, created = User.objects.get_or_create(
    email='demo@demo.com',
    defaults={
        'full_name': 'Demo User',
        'tenant': tenant,
        'role': role,
        'system_role': SystemRole.OWNER.value,
        'is_primary_owner': True
    }
)
if created:
    user.set_password('demo123')
    user.save()

print(f'Tenant ID: {tenant.id}')
print(f'User: {user.email}')
print(f'Password: demo123')
