from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.services import create_tenant_with_owner


class TestTenantIntegrations(APITestCase):
    def test_integrations_endpoint_returns_normalized_items(self):
        tenant, owner = create_tenant_with_owner(
            name="Integration Tenant",
            subdomain="integration-tenant",
            owner_email="owner@integration.com",
            owner_password="ownerpass123",
            owner_full_name="Integration Owner",
            integration_config={
                "integrations": [
                    {
                        "id": "airbnb",
                        "status": "connected",
                        "details": "4 propiedades sincronizadas",
                    },
                    {
                        "id": "custom-channel",
                        "name": "Custom Channel",
                        "description": "Sincronizacion personalizada",
                        "status": "pending",
                        "icon": "🧩",
                        "color": "#123456",
                    },
                ]
            },
        )
        self.client.force_authenticate(owner)

        response = self.client.get(f"/api/tenants/{tenant.id}/integrations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], "airbnb")
        self.assertEqual(response.data[0]["details"], "4 propiedades sincronizadas")
        self.assertEqual(response.data[-1]["id"], "custom-channel")
