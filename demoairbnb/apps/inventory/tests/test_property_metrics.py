from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from apps.booking.services import create_reservation
from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.inventory.models import Property


class TestPropertyMetrics(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name="Inventory Tenant",
            subdomain="inventory-tenant",
            owner_email="owner@inventory.com",
            owner_password="ownerpass123",
            owner_full_name="Inventory Owner",
        )
        self.client.force_authenticate(self.owner)

        self.property = Property.objects.create(
            tenant=self.tenant,
            name="Ocean View",
            address="Beach 123",
            capacity_adults=4,
            capacity_kids=2,
            base_price="200.00",
            cleaning_fee="50.00",
        )
        self.guest = Contact.objects.create(
            tenant=self.tenant,
            name="Inventory Guest",
            type=ContactType.GUEST,
            email="guest@inventory.com",
        )

        create_reservation(
            tenant_id=self.tenant.id,
            property_obj=self.property,
            guest=self.guest,
            check_in=date(2026, 3, 5),
            check_out=date(2026, 3, 8),
            created_by=self.owner,
        )

    def test_property_list_includes_monthly_revenue_and_occupancy_rate(self):
        response = self.client.get(
            f"/api/tenants/{self.tenant.id}/inventory/properties/?year=2026&month=3"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["monthly_revenue"], "650.00")
        self.assertEqual(response.data[0]["occupancy_rate"], 9.68)
