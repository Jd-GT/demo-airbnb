"""Tests for the mini-CRM stats endpoint per contact."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.booking.services import create_reservation
from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.finance.models import PaymentMethod, PaymentType
from apps.finance.services import register_payment
from apps.inventory.models import Property


class ContactStatsTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='CRM', subdomain='crm-stats',
            owner_email='c@c.com', owner_password='ownerpass123',
            owner_full_name='C',
        )
        self.prop = Property.all_objects.create(
            tenant=self.tenant, name='Apto', address='X',
            capacity_adults=2, base_price=Decimal('100'),
            cleaning_fee=Decimal('0'),
        )
        self.guest = Contact.all_objects.create(
            tenant=self.tenant, name='Juan', type=ContactType.GUEST.value,
            email='juan@example.com', tax_id='ABC-123',
        )
        # Two reservations: 3 nights and 2 nights
        self.r1 = create_reservation(
            tenant_id=self.tenant.id, property_obj=self.prop, guest=self.guest,
            check_in=date(2026, 1, 1), check_out=date(2026, 1, 4),
            created_by=self.owner,
        )
        self.r2 = create_reservation(
            tenant_id=self.tenant.id, property_obj=self.prop, guest=self.guest,
            check_in=date(2026, 5, 1), check_out=date(2026, 5, 3),
            created_by=self.owner,
        )
        # Pay r1 in full (300), partial on r2 (100), extra 50 on r1
        register_payment(
            reservation=self.r1, amount=Decimal('300'),
            method=PaymentMethod.CASH.value, type=PaymentType.BALANCE.value,
            date=date(2026, 1, 1),
        )
        register_payment(
            reservation=self.r2, amount=Decimal('100'),
            method=PaymentMethod.TRANSFER.value, type=PaymentType.ADVANCE.value,
            date=date(2026, 4, 25),
        )
        register_payment(
            reservation=self.r1, amount=Decimal('50'),
            method=PaymentMethod.CASH.value, type=PaymentType.EXTRA.value,
            date=date(2026, 1, 4), notes='Daño en lámpara',
        )

    def test_stats_endpoint(self):
        self.client.force_authenticate(self.owner)
        url = (
            f'/api/tenants/{self.tenant.id}/crm/contacts/{self.guest.id}/stats/'
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        data = resp.data
        self.assertEqual(data['reservations_count'], 2)
        self.assertEqual(data['confirmed_reservations_count'], 2)
        self.assertEqual(Decimal(data['total_billed']), Decimal('500.00'))
        self.assertEqual(Decimal(data['total_lodging_paid']), Decimal('400.00'))
        self.assertEqual(Decimal(data['total_extras_paid']), Decimal('50.00'))
        self.assertEqual(Decimal(data['outstanding_balance']), Decimal('100.00'))
        self.assertEqual(data['nights_total'], 5)
        self.assertEqual(str(data['first_check_in']), '2026-01-01')

    def test_contact_supports_tax_id_and_other_crm_fields(self):
        self.client.force_authenticate(self.owner)
        resp = self.client.patch(
            f'/api/tenants/{self.tenant.id}/crm/contacts/{self.guest.id}/',
            {
                'address': 'Calle 5 # 6-7',
                'nationality': 'CO',
                'notes': 'Cliente recurrente',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.address, 'Calle 5 # 6-7')
        self.assertEqual(self.guest.tax_id, 'ABC-123')
