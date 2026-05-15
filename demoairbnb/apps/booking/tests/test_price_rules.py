"""Tests for PriceRule and the dynamic-pricing branch of calculate_quote."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.booking.models import PriceRule
from apps.booking.services import calculate_quote
from apps.core.services import create_tenant_with_owner
from apps.crm.models import Contact, ContactType
from apps.inventory.models import Property


class CalculateQuoteWithRulesTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Pricing Tenant',
            subdomain='pricing-tenant',
            owner_email='owner@pricing.com',
            owner_password='ownerpass123',
            owner_full_name='Pricing Owner',
        )
        self.property = Property.all_objects.create(
            tenant=self.tenant,
            name='Apto Mar',
            address='X',
            capacity_adults=2,
            base_price=Decimal('100.00'),
            cleaning_fee=Decimal('20.00'),
        )

    def test_no_rules_uses_base_price(self):
        quote = calculate_quote(
            property_obj=self.property,
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 4),
        )
        self.assertEqual(quote.nights, 3)
        self.assertEqual(quote.subtotal_amount, Decimal('300.00'))
        self.assertEqual(quote.total_amount, Decimal('320.00'))
        self.assertEqual(quote.applied_rule_names, [])

    def test_percent_rule_applied(self):
        PriceRule.all_objects.create(
            tenant=self.tenant,
            name='Temporada Alta',
            start_date=date(2026, 12, 15),
            end_date=date(2027, 1, 10),
            is_percent=True,
            modifier=Decimal('1.50'),
            min_nights=2,
            priority=10,
        )
        quote = calculate_quote(
            property_obj=self.property,
            check_in=date(2026, 12, 20),
            check_out=date(2026, 12, 23),
        )
        self.assertEqual(quote.subtotal_amount, Decimal('450.00'))
        self.assertIn('Temporada Alta', quote.applied_rule_names)

    def test_min_nights_rejection(self):
        PriceRule.all_objects.create(
            tenant=self.tenant,
            name='Min 5 Navidad',
            start_date=date(2026, 12, 20),
            end_date=date(2026, 12, 31),
            is_percent=False,
            modifier=Decimal('200.00'),
            min_nights=5,
            priority=10,
        )
        from rest_framework.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            calculate_quote(
                property_obj=self.property,
                check_in=date(2026, 12, 22),
                check_out=date(2026, 12, 24),
            )

    def test_higher_priority_rule_wins(self):
        PriceRule.all_objects.create(
            tenant=self.tenant,
            name='Default temporada',
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            is_percent=False,
            modifier=Decimal('120.00'),
            priority=5,
        )
        PriceRule.all_objects.create(
            tenant=self.tenant,
            name='Promo fin de semana',
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            is_percent=False,
            modifier=Decimal('80.00'),
            priority=99,
        )
        quote = calculate_quote(
            property_obj=self.property,
            check_in=date(2026, 6, 5),
            check_out=date(2026, 6, 6),
        )
        # Promo wins (priority 99)
        self.assertEqual(quote.subtotal_amount, Decimal('80.00'))


class PriceRuleAPITests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='PR API',
            subdomain='pr-api',
            owner_email='pr@api.com',
            owner_password='ownerpass123',
            owner_full_name='PR Owner',
        )
        self.client.force_authenticate(self.owner)

    def test_owner_can_crud_price_rules(self):
        url = f'/api/tenants/{self.tenant.id}/booking/price-rules/'
        create_resp = self.client.post(
            url,
            {
                'name': 'Promo Octubre',
                'start_date': '2026-10-01',
                'end_date': '2026-10-31',
                'is_percent': True,
                'modifier': '0.80',
                'min_nights': 1,
                'priority': 10,
                'property_ids': [],
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED, create_resp.data)
        rule_id = create_resp.data['id']

        list_resp = self.client.get(url)
        self.assertEqual(len(list_resp.data), 1)

        delete_resp = self.client.delete(f'{url}{rule_id}/')
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)


class AgentCommissionTests(APITestCase):
    def test_create_reservation_computes_agent_commission(self):
        tenant, owner = create_tenant_with_owner(
            name='Commission',
            subdomain='commission',
            owner_email='c@commission.com',
            owner_password='ownerpass123',
            owner_full_name='Commission Owner',
        )
        self.client.force_authenticate(owner)
        prop = Property.all_objects.create(
            tenant=tenant, name='Casa', address='X',
            capacity_adults=2, base_price=Decimal('100'), cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=tenant, name='Guest', type=ContactType.GUEST.value
        )
        agent = Contact.all_objects.create(
            tenant=tenant, name='Daniel', type=ContactType.AGENT.value,
            commission_rate=Decimal('10.00'),
        )
        url = f'/api/tenants/{tenant.id}/booking/reservations/'
        resp = self.client.post(
            url,
            {
                'property_id': str(prop.id),
                'guest_id': str(guest.id),
                'agent_id': str(agent.id),
                'check_in': '2026-07-01',
                'check_out': '2026-07-04',
                'status': 'CONFIRMED',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        # 3 nights * 100 = 300; commission = 10% = 30
        self.assertEqual(Decimal(resp.data['agent_commission']), Decimal('30.00'))
        # Auto-generated reservation lines
        self.assertGreaterEqual(len(resp.data['lines']), 1)
