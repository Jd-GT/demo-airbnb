from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import User
from apps.core.services import create_tenant_with_owner


class JoinTenantRegistrationTests(APITestCase):
    def setUp(self):
        self.tenant, _ = create_tenant_with_owner(
            name='Join Tenant',
            subdomain='join-tenant',
            owner_email='owner@join-tenant.com',
            owner_password='ownerpass123',
            owner_full_name='Join Owner',
        )
        self.tenant.branding_config = {'invitation_code': 'JOIN123'}
        self.tenant.save(update_fields=['branding_config'])

    def test_join_registration_accepts_primary_join_field(self):
        payload = {
            'registration_type': 'join_tenant',
            'email': 'member1@join-tenant.com',
            'full_name': 'Member One',
            'password': 'memberpass123',
            'tenant_subdomain_join': self.tenant.subdomain,
            # Lowercase input should pass thanks to normalization.
            'invitation_code': 'join123',
        }

        response = self.client.post('/api/auth/register/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        member = User.objects.get(email=payload['email'])
        self.assertEqual(member.tenant_id, self.tenant.id)

    def test_join_registration_accepts_legacy_subdomain_field(self):
        payload = {
            'registration_type': 'join_tenant',
            'email': 'member2@join-tenant.com',
            'full_name': 'Member Two',
            'password': 'memberpass123',
            'tenant_subdomain': self.tenant.subdomain,
            'invitation_code': 'JOIN123',
        }

        response = self.client.post('/api/auth/register/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        member = User.objects.get(email=payload['email'])
        self.assertEqual(member.tenant_id, self.tenant.id)

    def test_join_registration_rejects_invalid_invitation_code(self):
        payload = {
            'registration_type': 'join_tenant',
            'email': 'member3@join-tenant.com',
            'full_name': 'Member Three',
            'password': 'memberpass123',
            'tenant_subdomain_join': self.tenant.subdomain,
            'invitation_code': 'WRONG',
        }

        response = self.client.post('/api/auth/register/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invitation_code', response.data)
