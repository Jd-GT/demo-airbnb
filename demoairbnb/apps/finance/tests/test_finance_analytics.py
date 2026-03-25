from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from apps.booking.services import create_reservation
from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.inventory.models import Property


class TestFinanceAnalytics(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Finance Tenant',
            subdomain='finance-tenant',
            owner_email='owner@finance.com',
            owner_password='ownerpass123',
            owner_full_name='Finance Owner',
        )
        self.client.force_authenticate(self.owner)

        self.property_a = Property.objects.create(
            tenant=self.tenant,
            name='Beach House',
            address='Beach 1',
            capacity_adults=4,
            capacity_kids=2,
            base_price='200.00',
            cleaning_fee='50.00',
        )
        self.property_b = Property.objects.create(
            tenant=self.tenant,
            name='Santo Domingo',
            address='City 1',
            capacity_adults=2,
            capacity_kids=0,
            base_price='150.00',
            cleaning_fee='25.00',
        )
        self.guest = Contact.objects.create(
            tenant=self.tenant,
            name='Guest Finance',
            type=ContactType.GUEST,
            email='guest@finance.com',
        )

        create_reservation(
            tenant_id=self.tenant.id,
            property_obj=self.property_a,
            guest=self.guest,
            check_in=date(2026, 3, 5),
            check_out=date(2026, 3, 8),
            created_by=self.owner,
        )
        create_reservation(
            tenant_id=self.tenant.id,
            property_obj=self.property_b,
            guest=self.guest,
            check_in=date(2026, 1, 10),
            check_out=date(2026, 1, 12),
            created_by=self.owner,
        )

    def test_finance_analytics_returns_totals_series_and_revenue_by_property(self):
        response = self.client.get(
            f'/api/tenants/{self.tenant.id}/finance/analytics/?year=2026&month=3'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['monthly_revenue_total'], '650.00')
        self.assertEqual(response.data['annual_revenue_total'], '975.00')
        self.assertEqual(len(response.data['monthly_revenue_series']), 12)
        self.assertEqual(
            response.data['monthly_revenue_series'][2]['ingresos'], '650.00'
        )
        self.assertEqual(len(response.data['revenue_by_property']), 2)
