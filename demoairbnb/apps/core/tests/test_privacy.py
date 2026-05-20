from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.constants import ModuleKey, PermissionLevel, SystemRole
from apps.core.models import TenantRole
from apps.core.services import create_tenant_user, create_tenant_with_owner


class PrivacyAndPermissionsTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Privacy Tenant',
            subdomain='privacy-tenant',
            owner_email='owner@privacy.com',
            owner_password='ownerpass123',
            owner_full_name='Privacy Owner',
            integration_config={
                'integrations': [
                    {
                        'id': 'google_calendar',
                        'status': 'connected',
                        'details': 'TOKEN_SECRET_DO_NOT_LEAK',
                    }
                ]
            },
        )
        self.member = create_tenant_user(
            tenant=self.tenant,
            email='member@privacy.com',
            password='memberpass123',
            full_name='Privacy Member',
            role=TenantRole.all_objects.get(tenant=self.tenant, name='Solo Lectura'),
            system_role=SystemRole.MEMBER.value,
        )

    def test_default_solo_lectura_role_has_no_users_or_finance(self):
        role = TenantRole.all_objects.get(tenant=self.tenant, name='Solo Lectura')
        self.assertEqual(
            role.permissions[ModuleKey.USERS.value], PermissionLevel.NONE.value
        )
        self.assertEqual(
            role.permissions[ModuleKey.FINANCE.value], PermissionLevel.NONE.value
        )
        self.assertEqual(
            role.permissions[ModuleKey.INVENTORY.value], PermissionLevel.READ.value
        )

    def test_member_cannot_list_other_users(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(f'/api/tenants/{self.tenant.id}/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_use_me_endpoint_for_self(self):
        self.client.force_authenticate(self.member)
        response = self.client.get('/api/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], self.member.email)
        self.assertEqual(
            response.data['permissions'][ModuleKey.USERS.value],
            PermissionLevel.NONE.value,
        )

    def test_member_cannot_see_integration_secrets(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(f'/api/tenants/{self.tenant.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['integration_config'], {})

    def test_owner_can_see_integration_secrets(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(f'/api/tenants/{self.tenant.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('integrations', response.data['integration_config'])

    def test_member_cannot_list_invitation_codes(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(
            f'/api/tenants/{self.tenant.id}/invitation-codes/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
