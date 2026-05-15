"""Allow PLATFORM contacts as guest (booking source like Airbnb/Booking)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.inventory.models import Property


class PlatformAsGuestTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Plat', subdomain='plat',
            owner_email='p@p.com', owner_password='ownerpass123',
            owner_full_name='P',
        )
        self.prop = Property.all_objects.create(
            tenant=self.tenant, name='Apto', address='X',
            capacity_adults=2, base_price=Decimal('100'),
            cleaning_fee=Decimal('0'),
        )
        self.airbnb = Contact.all_objects.create(
            tenant=self.tenant, name='Airbnb',
            type=ContactType.PLATFORM.value,
        )
        self.agent = Contact.all_objects.create(
            tenant=self.tenant, name='Daniel Agente',
            type=ContactType.AGENT.value,
        )

    def test_can_create_reservation_with_platform_as_guest(self):
        self.client.force_authenticate(self.owner)
        resp = self.client.post(
            f'/api/tenants/{self.tenant.id}/booking/reservations/',
            {
                'property_id': str(self.prop.id),
                'guest_id': str(self.airbnb.id),
                'check_in': '2026-09-01',
                'check_out': '2026-09-04',
                'status': 'CONFIRMED',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data['guest_name'], 'Airbnb')

    def test_agent_cannot_be_used_as_guest(self):
        self.client.force_authenticate(self.owner)
        resp = self.client.post(
            f'/api/tenants/{self.tenant.id}/booking/reservations/',
            {
                'property_id': str(self.prop.id),
                'guest_id': str(self.agent.id),
                'check_in': '2026-09-01',
                'check_out': '2026-09-04',
                'status': 'CONFIRMED',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('guest_id', resp.data)
