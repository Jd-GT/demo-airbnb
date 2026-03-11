from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.inventory.models import Property


class BookingSprintOneTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name="Booking Tenant",
            subdomain="booking-tenant",
            owner_email="owner@booking.com",
            owner_password="ownerpass123",
            owner_full_name="Booking Owner",
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
            name="Guest One",
            type=ContactType.GUEST,
            email="guest@booking.com",
        )

    def test_quote_availability_and_reservation_creation(self):
        check_in = date(2026, 4, 1)
        check_out = date(2026, 4, 4)

        quote_response = self.client.post(
            f"/api/tenants/{self.tenant.id}/booking/quote/",
            {
                "property_id": str(self.property.id),
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
            },
            format="json",
        )
        self.assertEqual(quote_response.status_code, status.HTTP_200_OK)
        self.assertEqual(quote_response.data["nights"], 3)
        self.assertEqual(quote_response.data["total_amount"], "650.00")

        create_response = self.client.post(
            f"/api/tenants/{self.tenant.id}/booking/reservations/",
            {
                "property_id": str(self.property.id),
                "guest_id": str(self.guest.id),
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        availability_response = self.client.post(
            f"/api/tenants/{self.tenant.id}/booking/reservations/availability/",
            {
                "property_id": str(self.property.id),
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
            },
            format="json",
        )
        self.assertEqual(availability_response.status_code, status.HTTP_200_OK)
        self.assertFalse(availability_response.data["available"])

        overlapping_response = self.client.post(
            f"/api/tenants/{self.tenant.id}/booking/reservations/",
            {
                "property_id": str(self.property.id),
                "guest_id": str(self.guest.id),
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
            },
            format="json",
        )
        self.assertEqual(overlapping_response.status_code, status.HTTP_400_BAD_REQUEST)
