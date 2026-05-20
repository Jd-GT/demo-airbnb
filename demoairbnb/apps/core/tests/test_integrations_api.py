from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.services import create_tenant_with_owner


class TestTenantIntegrations(APITestCase):
    def test_default_only_lists_google_calendar(self):
        tenant, owner = create_tenant_with_owner(
            name='Default Integrations Tenant',
            subdomain='default-integrations',
            owner_email='owner@default.com',
            owner_password='ownerpass123',
            owner_full_name='Default Owner',
        )
        self.client.force_authenticate(owner)

        response = self.client.get(f'/api/tenants/{tenant.id}/integrations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data]
        self.assertEqual(ids, ['google_calendar'])
        self.assertEqual(response.data[0]['status'], 'pending')

    def test_custom_integration_is_preserved(self):
        tenant, owner = create_tenant_with_owner(
            name='Custom Integrations Tenant',
            subdomain='custom-integrations',
            owner_email='owner@custom.com',
            owner_password='ownerpass123',
            owner_full_name='Custom Owner',
            integration_config={
                'integrations': [
                    {
                        'id': 'google_calendar',
                        'status': 'connected',
                        'details': '4 calendarios sincronizados',
                    },
                    {
                        'id': 'custom-channel',
                        'name': 'Custom Channel',
                        'description': 'Sincronizacion personalizada',
                        'status': 'pending',
                        'icon': '🧩',
                        'color': '#123456',
                    },
                ]
            },
        )
        self.client.force_authenticate(owner)

        response = self.client.get(f'/api/tenants/{tenant.id}/integrations/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items_by_id = {item['id']: item for item in response.data}
        self.assertEqual(items_by_id['google_calendar']['status'], 'connected')
        self.assertEqual(
            items_by_id['google_calendar']['details'], '4 calendarios sincronizados'
        )
        self.assertEqual(items_by_id['custom-channel']['name'], 'Custom Channel')
