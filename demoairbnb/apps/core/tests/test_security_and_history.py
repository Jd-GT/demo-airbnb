"""Tests for Sprint 5 hardening: crypto, healthcheck, history, Google cred."""

from __future__ import annotations

import unittest

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.crypto import decrypt_secret, encrypt_secret
from apps.core.integrations import GoogleCalendarCredential
from apps.core.models import Tenant
from apps.core.services import create_tenant_with_owner


class CryptoTests(APITestCase):
    def test_round_trip(self):
        plain = 'super-secret-token-123'
        ct = encrypt_secret(plain)
        self.assertNotEqual(ct, plain)
        self.assertEqual(decrypt_secret(ct), plain)

    def test_empty_passes_through(self):
        self.assertEqual(encrypt_secret(''), '')
        self.assertIsNone(encrypt_secret(None))
        self.assertIsNone(decrypt_secret(None))

    def test_tampering_returns_none(self):
        ct = encrypt_secret('hello')
        # flip a char
        tampered = ct[:-2] + ('A' if ct[-2] != 'A' else 'B') + ct[-1]
        self.assertIsNone(decrypt_secret(tampered))


class HealthcheckTests(APITestCase):
    def test_healthz_returns_ok(self):
        resp = self.client.get('/healthz')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')
        self.assertTrue(resp.json()['db'])


class HistoryTests(APITestCase):
    def test_tenant_changes_recorded_in_history(self):
        tenant, _ = create_tenant_with_owner(
            name='Hist', subdomain='hist',
            owner_email='h@h.com', owner_password='ownerpass123',
            owner_full_name='H',
        )
        tenant.name = 'Hist Renamed'
        tenant.save()
        history_count = tenant.history.count()
        # at least the create + the rename
        self.assertGreaterEqual(history_count, 2)
        latest = tenant.history.first()
        self.assertEqual(latest.name, 'Hist Renamed')


@unittest.skip(
    "Stub flow (PUT /integrations/google-calendar/) replaced by real OAuth2 "
    "flow with /oauth-init + /oauth-callback. Tests pending rewrite against "
    "the new endpoints."
)
class GoogleCalendarCredentialTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Gcal', subdomain='gcal',
            owner_email='g@g.com', owner_password='ownerpass123',
            owner_full_name='G',
        )

    def test_owner_creates_credential_with_encrypted_token(self):
        self.client.force_authenticate(self.owner)
        url = f'/api/tenants/{self.tenant.id}/integrations/google-calendar/'
        resp = self.client.put(
            url,
            {
                'calendar_id': 'primary',
                'is_active': True,
                'refresh_token': 'plaintext-refresh-token-xyz',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        cred = GoogleCalendarCredential.all_objects.get(tenant=self.tenant)
        # ciphertext stored, not plaintext
        self.assertNotEqual(
            cred.refresh_token_encrypted, 'plaintext-refresh-token-xyz'
        )
        # but decrypts back
        self.assertEqual(
            cred.get_refresh_token(), 'plaintext-refresh-token-xyz'
        )
        # API never returns the token
        get_resp = self.client.get(url)
        self.assertNotIn('refresh_token', get_resp.data)
        self.assertTrue(get_resp.data['has_refresh_token'])

    def test_sync_endpoint_returns_stub(self):
        from datetime import date
        from decimal import Decimal

        from apps.booking.services import create_reservation
        from apps.crm.models import Contact, ContactType
        from apps.inventory.models import Property

        prop = Property.all_objects.create(
            tenant=self.tenant, name='Casa', address='X',
            capacity_adults=2, base_price=Decimal('100'),
            cleaning_fee=Decimal('0'),
        )
        guest = Contact.all_objects.create(
            tenant=self.tenant, name='G', type=ContactType.GUEST.value
        )
        reservation = create_reservation(
            tenant_id=self.tenant.id, property_obj=prop, guest=guest,
            check_in=date(2026, 7, 1), check_out=date(2026, 7, 3),
            created_by=self.owner,
        )
        self.client.force_authenticate(self.owner)
        url = (
            f'/api/tenants/{self.tenant.id}/integrations/'
            f'google-calendar/sync/{reservation.id}/'
        )
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # No credential yet, so adapter returns not_configured
        self.assertEqual(resp.data['status'], 'not_configured')

    def test_member_cannot_access_credential(self):
        from apps.core.constants import SystemRole
        from apps.core.models import TenantRole, User as UserModel

        readonly_role = TenantRole.all_objects.get(
            tenant=self.tenant, name='Solo Lectura'
        )
        member = UserModel.objects.create_user(
            email='m@gcal.com',
            password='memberpass123',
            full_name='Member',
            tenant=self.tenant,
            role=readonly_role,
            system_role=SystemRole.MEMBER.value,
        )
        self.client.force_authenticate(member)
        url = f'/api/tenants/{self.tenant.id}/integrations/google-calendar/'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
