"""End-to-end coverage for Sprint 2/3 finance: payments, expenses, P&L, Excel."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.booking.services import create_reservation
from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.finance.models import (
    AnalyticAccount,
    AnalyticLine,
    AnalyticLineCategory,
    Payment,
    PaymentMethod,
    PaymentType,
    Tax,
)
from apps.finance.services import (
    accrue_reservation_income,
    build_pnl_xlsx,
    register_expense,
    register_payment,
)
from apps.inventory.models import Property


class CostCenterAutoCreationTests(APITestCase):
    def test_creating_property_auto_creates_cost_center(self):
        tenant, _ = create_tenant_with_owner(
            name='CC',
            subdomain='cc',
            owner_email='cc@cc.com',
            owner_password='ownerpass123',
            owner_full_name='CC',
        )
        prop = Property.all_objects.create(
            tenant=tenant, name='Apto 1', address='X',
            capacity_adults=2, base_price=Decimal('100'), cleaning_fee=Decimal('0'),
        )
        account = AnalyticAccount.all_objects.filter(
            tenant=tenant, property=prop
        ).first()
        self.assertIsNotNone(account)
        self.assertEqual(account.name, 'Centro costo — Apto 1')


class IncomeAccrualOnConfirmedReservationTests(APITestCase):
    def test_confirming_reservation_creates_income_line(self):
        tenant, owner = create_tenant_with_owner(
            name='Income',
            subdomain='income',
            owner_email='i@i.com',
            owner_password='ownerpass123',
            owner_full_name='Income Owner',
        )
        prop = Property.all_objects.create(
            tenant=tenant, name='Casa', address='X',
            capacity_adults=2, base_price=Decimal('100'), cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=tenant, name='G', type=ContactType.GUEST.value
        )
        reservation = create_reservation(
            tenant_id=tenant.id,
            property_obj=prop,
            guest=guest,
            check_in=date(2026, 5, 1),
            check_out=date(2026, 5, 4),
            created_by=owner,
        )
        income = AnalyticLine.all_objects.filter(
            tenant=tenant,
            reference_type='Reservation',
            reference_id=reservation.id,
            category=AnalyticLineCategory.INCOME.value,
        ).first()
        self.assertIsNotNone(income)
        self.assertEqual(income.amount, Decimal('300.00'))

    def test_accrual_is_idempotent(self):
        tenant, _ = create_tenant_with_owner(
            name='Idem',
            subdomain='idem',
            owner_email='idem@idem.com',
            owner_password='ownerpass123',
            owner_full_name='Idem',
        )
        prop = Property.all_objects.create(
            tenant=tenant, name='C', address='X',
            capacity_adults=2, base_price=Decimal('100'), cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=tenant, name='G', type=ContactType.GUEST.value
        )
        reservation = create_reservation(
            tenant_id=tenant.id,
            property_obj=prop,
            guest=guest,
            check_in=date(2026, 5, 1),
            check_out=date(2026, 5, 3),
        )
        accrue_reservation_income(reservation)  # second call
        count = AnalyticLine.all_objects.filter(
            reference_type='Reservation',
            reference_id=reservation.id,
            category=AnalyticLineCategory.INCOME.value,
        ).count()
        self.assertEqual(count, 1)


class PaymentLifecycleTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Pay',
            subdomain='pay',
            owner_email='pay@pay.com',
            owner_password='ownerpass123',
            owner_full_name='Pay Owner',
        )
        prop = Property.all_objects.create(
            tenant=self.tenant, name='C', address='X',
            capacity_adults=2, base_price=Decimal('200'), cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=self.tenant, name='G', type=ContactType.GUEST.value
        )
        self.reservation = create_reservation(
            tenant_id=self.tenant.id, property_obj=prop, guest=guest,
            check_in=date(2026, 8, 1), check_out=date(2026, 8, 3),
            created_by=self.owner,
        )
        # 2 nights * 200 = 400 total

    def test_partial_payment_updates_status(self):
        register_payment(
            reservation=self.reservation,
            amount=Decimal('200.00'),
            method=PaymentMethod.CASH.value,
            type=PaymentType.ADVANCE.value,
            date=date(2026, 7, 10),
            recorded_by=self.owner,
        )
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.amount_paid, Decimal('200.00'))
        self.assertEqual(self.reservation.payment_status, 'PARTIAL')

    def test_full_payment_marks_paid(self):
        register_payment(
            reservation=self.reservation,
            amount=Decimal('400.00'),
            method=PaymentMethod.TRANSFER.value,
            type=PaymentType.BALANCE.value,
            date=date(2026, 8, 1),
            recorded_by=self.owner,
        )
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.payment_status, 'PAID')

    def test_refund_decreases_amount_paid(self):
        register_payment(
            reservation=self.reservation, amount=Decimal('400.00'),
            method=PaymentMethod.TRANSFER.value, type=PaymentType.BALANCE.value,
            date=date(2026, 8, 1),
        )
        register_payment(
            reservation=self.reservation, amount=Decimal('100.00'),
            method=PaymentMethod.TRANSFER.value, type=PaymentType.REFUND.value,
            date=date(2026, 8, 5), notes='Reembolso parcial',
        )
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.amount_paid, Decimal('300.00'))
        self.assertEqual(self.reservation.payment_status, 'PARTIAL')

    def test_payment_endpoint_create_and_list(self):
        self.client.force_authenticate(self.owner)
        url = f'/api/tenants/{self.tenant.id}/finance/payments/'
        resp = self.client.post(
            url,
            {
                'reservation_id': str(self.reservation.id),
                'date': '2026-07-15',
                'amount': '150.00',
                'type': 'ADVANCE',
                'method': 'CASH',
                'reference': 'recibo-001',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        list_resp = self.client.get(url)
        self.assertEqual(len(list_resp.data), 1)


class ExpensesAndPnLTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='PnL', subdomain='pnl',
            owner_email='pnl@p.com', owner_password='ownerpass123',
            owner_full_name='PnL Owner',
        )
        self.prop = Property.all_objects.create(
            tenant=self.tenant, name='Apto', address='X',
            capacity_adults=2, base_price=Decimal('100'), cleaning_fee=Decimal('0'),
        )
        self.account = AnalyticAccount.all_objects.get(
            tenant=self.tenant, property=self.prop
        )
        guest = Contact.all_objects.create(
            tenant=self.tenant, name='G', type=ContactType.GUEST.value
        )
        create_reservation(
            tenant_id=self.tenant.id, property_obj=self.prop, guest=guest,
            check_in=date(2026, 6, 1), check_out=date(2026, 6, 5),  # 4 nights * 100 = 400
            created_by=self.owner,
        )

    def test_expense_creates_negative_line(self):
        line = register_expense(
            tenant_id=self.tenant.id,
            account=self.account,
            amount=Decimal('80.00'),
            category=AnalyticLineCategory.MAINTENANCE.value,
            date=date(2026, 6, 10),
            description='Cambio bombilla',
            recorded_by=self.owner,
        )
        self.assertEqual(line.amount, Decimal('-80.00'))

    def test_pnl_endpoint(self):
        register_expense(
            tenant_id=self.tenant.id, account=self.account,
            amount=Decimal('100.00'),
            category=AnalyticLineCategory.UTILITIES.value,
            date=date(2026, 6, 10),
        )
        self.client.force_authenticate(self.owner)
        url = (
            f'/api/tenants/{self.tenant.id}/finance/profit-and-loss/'
            f'?from_date=2026-06-01&to_date=2026-06-30'
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # income 400 (from confirmed reservation), expenses -100, net 300
        self.assertEqual(Decimal(resp.data['income']), Decimal('400.00'))
        self.assertEqual(Decimal(resp.data['expenses']), Decimal('-100.00'))
        self.assertEqual(Decimal(resp.data['net']), Decimal('300.00'))

    def test_pnl_xlsx_download(self):
        self.client.force_authenticate(self.owner)
        url = (
            f'/api/tenants/{self.tenant.id}/finance/reports/pnl.xlsx?year=2026'
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            resp['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertGreater(len(resp.content), 100)  # actually has bytes


class TaxAPITests(APITestCase):
    def test_tax_crud(self):
        tenant, owner = create_tenant_with_owner(
            name='T', subdomain='t',
            owner_email='t@t.com', owner_password='ownerpass123',
            owner_full_name='T',
        )
        self.client.force_authenticate(owner)
        url = f'/api/tenants/{tenant.id}/finance/taxes/'
        create_resp = self.client.post(
            url, {'name': 'IVA 19%', 'value': '0.19', 'type': 'PERCENT'}, format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        list_resp = self.client.get(url)
        self.assertEqual(len(list_resp.data), 1)
