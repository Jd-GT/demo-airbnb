"""Hardening: duplicates on Contact must return 400, never 500."""

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.services import create_tenant_with_owner


class ContactDuplicateValidationTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Dedup', subdomain='dedup',
            owner_email='d@d.com', owner_password='ownerpass123',
            owner_full_name='D',
        )
        self.client.force_authenticate(self.owner)
        self.url = f'/api/tenants/{self.tenant.id}/crm/contacts/'

    def test_duplicate_email_returns_400(self):
        first = self.client.post(
            self.url,
            {'name': 'Juan', 'email': 'j@j.com', 'type': 'GUEST'},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.client.post(
            self.url,
            {'name': 'Juan 2', 'email': 'J@J.com', 'type': 'GUEST'},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', second.data)

    def test_duplicate_tax_id_returns_400(self):
        first = self.client.post(
            self.url,
            {'name': 'Juan', 'tax_id': '1234567', 'type': 'GUEST'},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.client.post(
            self.url,
            {'name': 'Pedro', 'tax_id': '1234567', 'type': 'GUEST'},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tax_id', second.data)

    def test_empty_email_does_not_collide(self):
        # Two contacts without email must coexist
        for name in ['A', 'B', 'C']:
            r = self.client.post(
                self.url, {'name': name, 'type': 'GUEST'}, format='json'
            )
            self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
