from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import User
from apps.core.services import (
    create_tenant_with_owner,
    issue_create_tenant_code,
    issue_join_tenant_code,
)


class JoinTenantRegistrationTests(APITestCase):
    def setUp(self):
        self.tenant, _ = create_tenant_with_owner(
            name='Join Tenant',
            subdomain='join-tenant',
            owner_email='owner@join-tenant.com',
            owner_password='ownerpass123',
            owner_full_name='Join Owner',
        )
        self.invite = issue_join_tenant_code(
            tenant=self.tenant, max_uses=5, notes='Tests'
        )

    def test_join_with_valid_code_and_subdomain(self):
        payload = {
            'invitation_code': self.invite.code.lower(),  # case-insensitive
            'tenant_subdomain_join': self.tenant.subdomain,
            'email': 'member1@join-tenant.com',
            'full_name': 'Member One',
            'password': 'memberpass123',
        }
        response = self.client.post('/api/auth/register/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        member = User.objects.get(email=payload['email'])
        self.assertEqual(member.tenant_id, self.tenant.id)

    def test_join_without_subdomain_still_works(self):
        # The code itself identifies the tenant. Subdomain is only a confirmation.
        payload = {
            'invitation_code': self.invite.code,
            'email': 'member2@join-tenant.com',
            'full_name': 'Member Two',
            'password': 'memberpass123',
        }
        response = self.client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        member = User.objects.get(email=payload['email'])
        self.assertEqual(member.tenant_id, self.tenant.id)

    def test_join_rejects_subdomain_mismatch(self):
        payload = {
            'invitation_code': self.invite.code,
            'tenant_subdomain_join': 'some-other-tenant',
            'email': 'member3@join-tenant.com',
            'full_name': 'Member Three',
            'password': 'memberpass123',
        }
        response = self.client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tenant_subdomain_join', response.data)

    def test_join_rejects_invalid_invitation_code(self):
        payload = {
            'invitation_code': 'NOTACODE12',
            'tenant_subdomain_join': self.tenant.subdomain,
            'email': 'member4@join-tenant.com',
            'full_name': 'Member Four',
            'password': 'memberpass123',
        }
        response = self.client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invitation_code', response.data)

    def test_create_tenant_code_cannot_be_used_to_join_existing(self):
        create_invite = issue_create_tenant_code()
        payload = {
            'invitation_code': create_invite.code,
            'tenant_subdomain_join': self.tenant.subdomain,
            'email': 'member5@join-tenant.com',
            'full_name': 'Member Five',
            'password': 'memberpass123',
        }
        # CREATE_TENANT codes require new-tenant fields, so this should fail
        # because tenant_name/tenant_subdomain are missing.
        response = self.client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
