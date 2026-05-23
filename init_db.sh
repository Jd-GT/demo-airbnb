#!/bin/bash
set -e

cd /app

echo "Running migrations..."
python demoairbnb/manage.py migrate --noinput

echo "Bootstrapping superusers, demo tenant and invitation code..."
python <<'PYEOF'
import os
import sys

sys.path.insert(0, '/app/demoairbnb')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demoairbnb.settings')

import django
django.setup()

from datetime import date, timedelta

from django.contrib.auth import get_user_model

from apps.booking.models import Reservation
from apps.core.constants import (
    PermissionLevel,
    SystemRole,
    modules_default_permissions,
)
from apps.core.models import (
    InvitationCode,
    InvitationCodePurpose,
    Tenant,
    TenantRole,
)
from apps.core.services import issue_create_tenant_code
from apps.crm.models import Contact
from apps.inventory.models import Property

User = get_user_model()

# --- Platform super-admins (operators of the SaaS) ---
# Read from env so production credentials never live in the repo. Local
# dev keeps the historical defaults so `docker compose up` still works.
admins = [
    {
        'email': os.environ.get('SUPERADMIN_EMAIL_1', 'admin@admin.com'),
        'password': os.environ.get('SUPERADMIN_PASSWORD_1', 'admin123'),
        'full_name': 'Admin Superuser',
    },
    {
        'email': os.environ.get('SUPERADMIN_EMAIL_2', 'afprietol2005@gmail.com'),
        'password': os.environ.get('SUPERADMIN_PASSWORD_2', 'changeme-set-env'),
        'full_name': 'Andres Prieto',
    },
]
for cfg in admins:
    if not cfg['email']:
        continue
    try:
        user = User.objects.get(email=cfg['email'])
    except User.DoesNotExist:
        # create_user goes through the manager which calls set_password()
        # *before* save() so full_clean() doesn't trip on an empty hash.
        User.objects.create_user(
            email=cfg['email'],
            password=cfg['password'],
            full_name=cfg['full_name'],
            is_superuser=True,
            is_staff=True,
        )
        print('Superuser CREATED: ' + cfg['email'])
        continue
    changed = False
    if not user.is_superuser or not user.is_staff:
        user.is_superuser = True
        user.is_staff = True
        changed = True
    if os.environ.get('SUPERADMIN_RESET') == '1' and cfg['password']:
        user.set_password(cfg['password'])
        changed = True
    if changed:
        user.save()
        print('Superuser refreshed: ' + cfg['email'])
    else:
        print('Superuser already present: ' + cfg['email'])

# --- Demo tenant (seed only when SEED_DEMO_TENANT != 0) ---
demo_seed = os.environ.get('SEED_DEMO_TENANT', '1') != '0'
if demo_seed:
    tenant, _ = Tenant.objects.get_or_create(
        subdomain='demo',
        defaults={'name': 'Demo Tenant', 'is_active': True},
    )
    # Only flip is_default when no other role already holds it (the
    # constraint allows a single default per tenant).
    has_default = TenantRole.all_objects.filter(
        tenant=tenant, is_default=True
    ).exists()
    role, _ = TenantRole.objects.get_or_create(
        tenant=tenant,
        name='Admin Total',
        defaults={
            'permissions': modules_default_permissions(PermissionLevel.ADMIN),
            'is_default': not has_default,
        },
    )
    if not User.objects.filter(email='demo@demo.com').exists():
        User.objects.create_user(
            email='demo@demo.com',
            password='demo123',
            full_name='Demo Owner',
            tenant=tenant,
            role=role,
            system_role=SystemRole.OWNER.value,
            is_primary_owner=True,
        )
        print('Demo tenant owner created: demo@demo.com / demo123')

    prop1, _ = Property.objects.get_or_create(
        tenant=tenant, name='Apartamento Centro',
        defaults={
            'address': 'Calle 10 #5-30', 'capacity_adults': 4,
            'capacity_kids': 2, 'base_price': '150000',
            'cleaning_fee': '50000',
        },
    )
    prop2, _ = Property.objects.get_or_create(
        tenant=tenant, name='Casa Playa',
        defaults={
            'address': 'Carrera 5 #12-45', 'capacity_adults': 6,
            'capacity_kids': 3, 'base_price': '250000',
            'cleaning_fee': '80000',
        },
    )
    prop3, _ = Property.objects.get_or_create(
        tenant=tenant, name='Loft Moderno',
        defaults={
            'address': 'Avenida 15 #8-20', 'capacity_adults': 2,
            'capacity_kids': 1, 'base_price': '120000',
            'cleaning_fee': '40000',
        },
    )

    guest1, _ = Contact.objects.get_or_create(
        tenant=tenant, email='juan@example.com',
        defaults={
            'name': 'Juan Perez', 'phone': '+573001234567',
            'type': 'GUEST',
        },
    )
    guest2, _ = Contact.objects.get_or_create(
        tenant=tenant, email='maria@example.com',
        defaults={
            'name': 'Maria Garcia', 'phone': '+573009876543',
            'type': 'GUEST',
        },
    )
    guest3, _ = Contact.objects.get_or_create(
        tenant=tenant, email='carlos@example.com',
        defaults={
            'name': 'Carlos Lopez', 'phone': '+573001112233',
            'type': 'GUEST',
        },
    )

    today = date.today()
    Reservation.objects.get_or_create(
        tenant=tenant, property=prop1, guest=guest1,
        defaults={
            'check_in': today, 'check_out': today + timedelta(days=3),
            'status': 'CONFIRMED', 'nights': 3,
            'subtotal_amount': '450000', 'cleaning_fee': '50000',
            'total_amount': '500000',
        },
    )
    Reservation.objects.get_or_create(
        tenant=tenant, property=prop2, guest=guest2,
        defaults={
            'check_in': today + timedelta(days=5),
            'check_out': today + timedelta(days=8),
            'status': 'CONFIRMED', 'nights': 3,
            'subtotal_amount': '750000', 'cleaning_fee': '80000',
            'total_amount': '830000',
        },
    )
    Reservation.objects.get_or_create(
        tenant=tenant, property=prop3, guest=guest3,
        defaults={
            'check_in': today - timedelta(days=2),
            'check_out': today + timedelta(days=1),
            'status': 'CONFIRMED', 'nights': 3,
            'subtotal_amount': '360000', 'cleaning_fee': '40000',
            'total_amount': '400000',
        },
    )
    print('Demo tenant id=%s subdomain=demo' % tenant.id)
    print('Demo data: properties=%d reservations=%d' % (
        Property.objects.filter(tenant=tenant).count(),
        Reservation.objects.filter(tenant=tenant).count(),
    ))

# --- Bootstrap CREATE_TENANT invitation code (single-use). Allows
# whoever lands on /login to register a brand new tenant without
# touching the Django admin first.
if not InvitationCode.objects.filter(
    purpose=InvitationCodePurpose.CREATE_TENANT.value, is_active=True
).exists():
    invite = issue_create_tenant_code(
        notes='Bootstrap CREATE_TENANT code generated by init_db.sh',
        max_uses=int(os.environ.get('BOOTSTRAP_CODE_USES', '1')),
    )
    print('Bootstrap CREATE_TENANT invitation code: ' + invite.code)
    print('  -> use it once from /login to register a new tenant.')
PYEOF

# Collect static files when STATIC_ROOT is configured (prod).
python demoairbnb/manage.py collectstatic --noinput 2>/dev/null || \
    echo "(collectstatic skipped - dev or STATIC_ROOT missing)"

echo "Starting server..."
if [ "${DJANGO_SERVER:-runserver}" = "gunicorn" ]; then
    cd /app/demoairbnb
    exec gunicorn demoairbnb.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "${GUNICORN_WORKERS:-3}" \
        --timeout "${GUNICORN_TIMEOUT:-60}" \
        --access-logfile - \
        --error-logfile -
else
    exec python demoairbnb/manage.py runserver 0.0.0.0:8000
fi
