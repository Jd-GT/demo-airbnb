from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from apps.booking.services import create_reservation
from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.inventory.models import Property


class TestReservationFilters(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name="Reservation Tenant",
            subdomain="reservation-tenant",
            owner_email="owner@reservation.com",
            owner_password="ownerpass123",
            owner_full_name="Reservation Owner",
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
            name="Reservation Guest",
            type=ContactType.GUEST,
            email="guest@reservation.com",
        )

        create_reservation(
            tenant_id=self.tenant.id,
            property_obj=self.property,
            guest=self.guest,
            check_in=date(2026, 3, 5),
            check_out=date(2026, 3, 8),
            created_by=self.owner,
        )
        create_reservation(
            tenant_id=self.tenant.id,
            property_obj=self.property,
            guest=self.guest,
            check_in=date(2026, 4, 10),
            check_out=date(2026, 4, 12),
            created_by=self.owner,
        )

    def test_reservation_list_filters_by_range_and_returns_names(self):
        response = self.client.get(
            f"/api/tenants/{self.tenant.id}/booking/reservations/?from=2026-03-01&to=2026-04-01"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["property_name"], "Ocean View")
        self.assertEqual(response.data[0]["guest_name"], "Reservation Guest")
