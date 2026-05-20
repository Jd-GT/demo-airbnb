from __future__ import annotations

from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.services import create_tenant_with_owner


class AuthApiTests(APITestCase):
    def setUp(self):
        self.tenant, self.owner = create_tenant_with_owner(
            name="Auth Tenant",
            subdomain="auth-tenant",
            owner_email="owner@auth.com",
            owner_password="ownerpass123",
            owner_full_name="Auth Owner",
        )

    def test_token_response_includes_tokens_and_user_data(self):
        response = self.client.post(
            "/api/auth/token/",
            {
                "email": "owner@auth.com",
                "password": "ownerpass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertEqual(response.data["access"], response.data["access_token"])
        self.assertEqual(response.data["refresh"], response.data["refresh_token"])
        self.assertEqual(
            response.data["user"],
            {
                "id": str(self.owner.id),
                "email": self.owner.email,
                "full_name": self.owner.full_name,
                "system_role": self.owner.system_role,
                "tenant_id": str(self.tenant.id),
            },
        )

    def test_logout_requires_valid_authorization_header(self):
        anonymous_response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)

        token_response = self.client.post(
            "/api/auth/token/",
            {
                "email": "owner@auth.com",
                "password": "ownerpass123",
            },
            format="json",
        )
        access_token = token_response.data["access_token"]

        logout_response = self.client.post(
            "/api/auth/logout/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
            format="json",
        )

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            logout_response.data,
            {"message": "Logged out successfully"},
        )
