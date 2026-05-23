from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.constants import SystemRole
from apps.core.models import TenantRole, User
from apps.core.services import (
    create_tenant_user,
    create_tenant_with_owner,
    issue_create_tenant_code,
)


class TenantBootstrapTests(APITestCase):
    def test_signup_with_create_tenant_code_seeds_roles_and_owner(self):
        invite = issue_create_tenant_code(notes='test')

        payload = {
            'invitation_code': invite.code,
            'tenant_name': 'Tenant A',
            'tenant_subdomain': 'tenant-a',
            'email': 'owner@a.com',
            'full_name': 'Owner A',
            'password': 'ownerpass123',
        }

        response = self.client.post('/api/auth/register/', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        tenant_id = response.data['tenant']['id']

        roles = TenantRole.all_objects.filter(tenant_id=tenant_id)
        self.assertSetEqual(
            set(roles.values_list('name', flat=True)), {'Admin Total', 'Solo Lectura'}
        )

        owner = User.objects.get(email='owner@a.com')
        self.assertEqual(str(owner.tenant_id), tenant_id)
        self.assertEqual(owner.system_role, SystemRole.OWNER.value)
        self.assertTrue(owner.is_primary_owner)

        invite.refresh_from_db()
        self.assertEqual(invite.uses_count, 1)
        self.assertFalse(invite.is_active, 'Single-use code should self-deactivate')

    def test_signup_without_invitation_code_is_rejected(self):
        payload = {
            'tenant_name': 'Tenant Sin Código',
            'tenant_subdomain': 'tenant-no-code',
            'email': 'noone@nocode.com',
            'full_name': 'NoCode',
            'password': 'pass123456',
        }
        response = self.client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('invitation_code', response.data)

    def test_public_tenant_create_endpoint_is_disabled(self):
        # POST /api/tenants/ used to allow public tenant creation. Now removed.
        response = self.client.post(
            '/api/tenants/',
            {'name': 'Bypass', 'subdomain': 'bypass'},
            format='json',
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_405_METHOD_NOT_ALLOWED),
        )


class OwnerProtectionTests(APITestCase):
    def test_primary_owner_cannot_be_deactivated_or_downgraded(self):
        tenant, owner = create_tenant_with_owner(
            name='Tenant B',
            subdomain='tenant-b',
            owner_email='owner@b.com',
            owner_password='ownerpass123',
            owner_full_name='Owner B',
        )
        self.client.force_authenticate(owner)

        url = f'/api/tenants/{tenant.id}/users/{owner.id}/'

        deactivate_response = self.client.patch(
            url, {'is_active': False}, format='json'
        )
        self.assertEqual(deactivate_response.status_code, status.HTTP_400_BAD_REQUEST)

        downgrade_response = self.client.patch(
            url,
            {'system_role': SystemRole.MEMBER.value},
            format='json',
        )
        self.assertEqual(downgrade_response.status_code, status.HTTP_400_BAD_REQUEST)


class TenantIsolationAndRBAC(APITestCase):
    def setUp(self):
        self.tenant_a, self.owner_a = create_tenant_with_owner(
            name='Tenant C',
            subdomain='tenant-c',
            owner_email='owner@c.com',
            owner_password='ownerpass123',
            owner_full_name='Owner C',
        )
        self.tenant_b, self.owner_b = create_tenant_with_owner(
            name='Tenant D',
            subdomain='tenant-d',
            owner_email='owner@d.com',
            owner_password='ownerpass123',
            owner_full_name='Owner D',
        )

    def test_user_cannot_operate_in_other_tenant(self):
        self.client.force_authenticate(self.owner_a)

        create_in_a = self.client.post(
            f'/api/tenants/{self.tenant_a.id}/inventory/properties/',
            {
                'name': 'Apto 101',
                'address': 'Street 1',
                'capacity_adults': 2,
                'capacity_kids': 1,
                'base_price': '100.00',
                'cleaning_fee': '20.00',
            },
            format='json',
        )
        self.assertEqual(create_in_a.status_code, status.HTTP_201_CREATED)

        create_in_b = self.client.post(
            f'/api/tenants/{self.tenant_b.id}/inventory/properties/',
            {
                'name': 'Cross Tenant',
                'address': 'Forbidden',
                'capacity_adults': 2,
                'capacity_kids': 0,
                'base_price': '90.00',
                'cleaning_fee': '10.00',
            },
            format='json',
        )
        self.assertEqual(create_in_b.status_code, status.HTTP_403_FORBIDDEN)

    def test_readonly_role_cannot_write_inventory(self):
        readonly_role = TenantRole.all_objects.get(
            tenant=self.tenant_a, name='Solo Lectura'
        )
        member = create_tenant_user(
            tenant=self.tenant_a,
            email='member@tenantc.com',
            password='memberpass123',
            full_name='Read Only',
            role=readonly_role,
            system_role=SystemRole.MEMBER.value,
        )

        self.client.force_authenticate(member)

        create_response = self.client.post(
            f'/api/tenants/{self.tenant_a.id}/inventory/properties/',
            {
                'name': 'Apto 102',
                'address': 'Street 2',
                'capacity_adults': 2,
                'capacity_kids': 0,
                'base_price': '120.00',
                'cleaning_fee': '25.00',
            },
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

        list_response = self.client.get(
            f'/api/tenants/{self.tenant_a.id}/inventory/properties/'
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
