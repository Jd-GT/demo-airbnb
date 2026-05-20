from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.constants import PermissionLevel, SystemRole, modules_default_permissions
from apps.core.models import InvitationCode, TenantRole
from apps.core.services import create_tenant_user, create_tenant_with_owner


class InvitationCodeManagementTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name='Invite Tenant',
            subdomain='invite-tenant',
            owner_email='owner@invite.com',
            owner_password='ownerpass123',
            owner_full_name='Invite Owner',
        )
        self.list_url = f'/api/tenants/{self.tenant.id}/invitation-codes/'

    def test_owner_can_create_join_code(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.list_url,
            {'max_uses': 3, 'notes': 'Equipo nuevo'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['max_uses'], 3)
        self.assertEqual(response.data['purpose'], 'JOIN_TENANT')
        self.assertTrue(response.data['code'])
        self.assertEqual(response.data['tenant_subdomain'], 'invite-tenant')

    def test_owner_can_list_codes(self):
        self.client.force_authenticate(self.owner)
        self.client.post(self.list_url, {'max_uses': 1}, format='json')
        self.client.post(self.list_url, {'max_uses': 1}, format='json')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_member_with_only_read_permission_cannot_list_codes(self):
        readonly_role = TenantRole.all_objects.get(
            tenant=self.tenant, name='Solo Lectura'
        )
        member = create_tenant_user(
            tenant=self.tenant,
            email='reader@invite.com',
            password='memberpass123',
            full_name='Reader',
            role=readonly_role,
            system_role=SystemRole.MEMBER.value,
        )
        self.client.force_authenticate(member)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_deactivates_code(self):
        self.client.force_authenticate(self.owner)
        create_response = self.client.post(self.list_url, {'max_uses': 1}, format='json')
        code_id = create_response.data['id']
        delete_response = self.client.delete(f'{self.list_url}{code_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        invite = InvitationCode.objects.get(id=code_id)
        self.assertFalse(invite.is_active)

    def test_cross_tenant_access_is_forbidden(self):
        other_tenant, _ = create_tenant_with_owner(
            name='Other',
            subdomain='other-invite',
            owner_email='other@invite.com',
            owner_password='ownerpass123',
            owner_full_name='Other',
        )
        self.client.force_authenticate(self.owner)
        response = self.client.get(
            f'/api/tenants/{other_tenant.id}/invitation-codes/'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
