#!/bin/bash
set -e

cd /app

echo "Running migrations..."
python demoairbnb/manage.py migrate --noinput

echo "Creating demo tenant..."
python -c "
import os
import sys
sys.path.insert(0, '/app/demoairbnb')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demoairbnb.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from apps.core.models import Tenant, TenantRole
from apps.inventory.models import Property
from apps.booking.models import Reservation
from apps.crm.models import Contact
from apps.core.constants import SystemRole, PermissionLevel, modules_default_permissions
from datetime import date, timedelta

User = get_user_model()

# Create superuser for admin panel
try:
    superuser = User.objects.get(email='admin@admin.com')
except User.DoesNotExist:
    superuser = User.objects.create_superuser(
        email='admin@admin.com',
        password='admin123',
        full_name='Admin Superuser'
    )
    print('Superuser created: admin@admin.com / admin123')

tenant, created = Tenant.objects.get_or_create(subdomain='demo', defaults={'name': 'Demo Tenant', 'is_active': True})
if not created:
    tenant.branding_config = {'invitation_code': 'DEMO123'}
    tenant.save()

role, _ = TenantRole.objects.get_or_create(tenant=tenant, name='Admin', defaults={'permissions': modules_default_permissions(PermissionLevel.ADMIN), 'is_default': True})

try:
    user = User.objects.get(email='demo@demo.com')
except User.DoesNotExist:
    user = User.objects.create_user(
        email='demo@demo.com',
        password='demo123',
        full_name='Demo User',
        tenant=tenant,
        role=role,
        system_role=SystemRole.OWNER.value,
        is_primary_owner=True
    )

prop1, _ = Property.objects.get_or_create(tenant=tenant, name='Apartamento Centro', defaults={'address': 'Calle 10 #5-30', 'capacity_adults': 4, 'capacity_kids': 2, 'base_price': '150000', 'cleaning_fee': '50000'})
prop2, _ = Property.objects.get_or_create(tenant=tenant, name='Casa Playa', defaults={'address': 'Carrera 5 #12-45', 'capacity_adults': 6, 'capacity_kids': 3, 'base_price': '250000', 'cleaning_fee': '80000'})
prop3, _ = Property.objects.get_or_create(tenant=tenant, name='Loft Moderno', defaults={'address': 'Avenida 15 #8-20', 'capacity_adults': 2, 'capacity_kids': 1, 'base_price': '120000', 'cleaning_fee': '40000'})

guest1, _ = Contact.objects.get_or_create(tenant=tenant, email='juan@example.com', defaults={'name': 'Juan Perez', 'phone': '+573001234567', 'type': 'GUEST'})
guest2, _ = Contact.objects.get_or_create(tenant=tenant, email='maria@example.com', defaults={'name': 'Maria Garcia', 'phone': '+573009876543', 'type': 'GUEST'})
guest3, _ = Contact.objects.get_or_create(tenant=tenant, email='carlos@example.com', defaults={'name': 'Carlos Lopez', 'phone': '+573001112233', 'type': 'GUEST'})

today = date.today()

res1, _ = Reservation.objects.get_or_create(
    tenant=tenant, property=prop1, guest=guest1,
    defaults={'check_in': today, 'check_out': today + timedelta(days=3), 'status': 'CONFIRMED', 'nights': 3, 'subtotal_amount': '450000', 'cleaning_fee': '50000', 'total_amount': '500000'}
)
res2, _ = Reservation.objects.get_or_create(
    tenant=tenant, property=prop2, guest=guest2,
    defaults={'check_in': today + timedelta(days=5), 'check_out': today + timedelta(days=8), 'status': 'CONFIRMED', 'nights': 3, 'subtotal_amount': '750000', 'cleaning_fee': '80000', 'total_amount': '830000'}
)
res3, _ = Reservation.objects.get_or_create(
    tenant=tenant, property=prop3, guest=guest3,
    defaults={'check_in': today - timedelta(days=2), 'check_out': today + timedelta(days=1), 'status': 'CONFIRMED', 'nights': 3, 'subtotal_amount': '360000', 'cleaning_fee': '40000', 'total_amount': '400000'}
)

print('Tenant ID:', tenant.id)
print('User: demo@demo.com')
print('Password: demo123')
print('Properties:', Property.objects.filter(tenant=tenant).count())
print('Reservations:', Reservation.objects.filter(tenant=tenant).count())
"

echo "Starting server..."
python demoairbnb/manage.py runserver 0.0.0.0:8000
