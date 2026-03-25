from django.urls import path

from .views import TenantIntegrationsView, TenantRoleViewSet, TenantUserViewSet, TenantViewSet


tenant_list = TenantViewSet.as_view({"get": "list", "post": "create"})
tenant_detail = TenantViewSet.as_view({"get": "retrieve"})

role_list = TenantRoleViewSet.as_view({"get": "list", "post": "create"})
role_detail = TenantRoleViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"})

user_list = TenantUserViewSet.as_view({"get": "list", "post": "create"})
user_detail = TenantUserViewSet.as_view({"get": "retrieve", "patch": "partial_update"})

urlpatterns = [
    path("tenants/", tenant_list, name="tenant-list"),
    path("tenants/<uuid:pk>/", tenant_detail, name="tenant-detail"),
    path("tenants/<uuid:tenant_id>/roles/", role_list, name="tenant-role-list"),
    path("tenants/<uuid:tenant_id>/roles/<uuid:role_id>/", role_detail, name="tenant-role-detail"),
    path("tenants/<uuid:tenant_id>/users/", user_list, name="tenant-user-list"),
    path("tenants/<uuid:tenant_id>/users/<uuid:user_id>/", user_detail, name="tenant-user-detail"),
    path("tenants/<uuid:tenant_id>/integrations/", TenantIntegrationsView.as_view(), name="tenant-integrations"),
]
