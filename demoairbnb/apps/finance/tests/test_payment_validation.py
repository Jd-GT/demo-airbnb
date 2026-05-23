"""Sprint 3.5 — overpayment validation + EXTRA payments + extras_received."""

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


class OverpaymentValidationTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='OP', subdomain='op',
            owner_email='op@op.com', owner_password='ownerpass123',
            owner_full_name='OP',
        )
        prop = Property.all_objects.create(
            tenant=self.tenant, name='C', address='X',
            capacity_adults=2, base_price=Decimal('100'),
            cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=self.tenant, name='G', type=ContactType.GUEST.value
        )
        self.reservation = create_reservation(
            tenant_id=self.tenant.id, property_obj=prop, guest=guest,
            check_in=date(2026, 8, 1), check_out=date(2026, 8, 5),
            created_by=self.owner,
        )
        # 4 nights * 100 = 400 total

    def test_lodging_payment_cannot_exceed_balance(self):
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            register_payment(
                reservation=self.reservation,
                amount=Decimal('500.00'),  # > 400 total
                method=PaymentMethod.CASH.value,
                type=PaymentType.ADVANCE.value,
                date=date(2026, 7, 10),
                recorded_by=self.owner,
            )

    def test_lodging_overpayment_via_partial_then_full_blocked(self):
        from rest_framework.exceptions import ValidationError

        register_payment(
            reservation=self.reservation, amount=Decimal('200.00'),
            method=PaymentMethod.CASH.value, type=PaymentType.ADVANCE.value,
            date=date(2026, 7, 10),
        )
        # Now balance is 200. Trying to pay 250 should fail.
        with self.assertRaises(ValidationError):
            register_payment(
                reservation=self.reservation, amount=Decimal('250.00'),
                method=PaymentMethod.CASH.value, type=PaymentType.BALANCE.value,
                date=date(2026, 8, 1),
            )

    def test_extra_payment_has_no_upper_bound(self):
        # EXTRA payments don't count against lodging balance and have no cap.
        register_payment(
            reservation=self.reservation, amount=Decimal('400.00'),
            method=PaymentMethod.CASH.value, type=PaymentType.BALANCE.value,
            date=date(2026, 8, 1),
        )
        register_payment(
            reservation=self.reservation, amount=Decimal('99999.00'),
            method=PaymentMethod.CASH.value, type=PaymentType.EXTRA.value,
            date=date(2026, 8, 5), notes='Daño en TV',
        )
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.amount_paid, Decimal('400.00'))
        self.assertEqual(self.reservation.extras_received, Decimal('99999.00'))
        self.assertEqual(self.reservation.payment_status, 'PAID')

    def test_payment_endpoint_returns_400_on_overpayment(self):
        self.client.force_authenticate(self.owner)
        url = f'/api/tenants/{self.tenant.id}/finance/payments/'
        resp = self.client.post(
            url,
            {
                'reservation_id': str(self.reservation.id),
                'date': '2026-07-15',
                'amount': '600.00',
                'type': 'ADVANCE',
                'method': 'CASH',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', resp.data)

    def test_refund_cannot_exceed_paid(self):
        from rest_framework.exceptions import ValidationError

        register_payment(
            reservation=self.reservation, amount=Decimal('100.00'),
            method=PaymentMethod.CASH.value, type=PaymentType.ADVANCE.value,
            date=date(2026, 7, 10),
        )
        with self.assertRaises(ValidationError):
            register_payment(
                reservation=self.reservation, amount=Decimal('500.00'),
                method=PaymentMethod.TRANSFER.value, type=PaymentType.REFUND.value,
                date=date(2026, 7, 15),
            )
