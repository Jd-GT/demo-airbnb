from django.urls import path

from .views import (
    CurrentUserView,
    GoogleCalendarCredentialView,
    GoogleCalendarSyncTriggerView,
    InvitationCodeViewSet,
    TenantIntegrationsView,
    TenantRoleViewSet,
    TenantUserViewSet,
    TenantViewSet,
    UserRegistrationView,
)

tenant_list = TenantViewSet.as_view({'get': 'list'})
tenant_detail = TenantViewSet.as_view(
    {'get': 'retrieve', 'patch': 'partial_update', 'put': 'update'}
)

role_list = TenantRoleViewSet.as_view({'get': 'list', 'post': 'create'})
role_detail = TenantRoleViewSet.as_view(
    {'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}
)

user_list = TenantUserViewSet.as_view({'get': 'list', 'post': 'create'})
user_detail = TenantUserViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'})

invitation_list = InvitationCodeViewSet.as_view({'get': 'list', 'post': 'create'})
invitation_detail = InvitationCodeViewSet.as_view(
    {'get': 'retrieve', 'delete': 'destroy'}
)

urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='user-register'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('tenants/', tenant_list, name='tenant-list'),
    path('tenants/<uuid:pk>/', tenant_detail, name='tenant-detail'),
    path('tenants/<uuid:tenant_id>/roles/', role_list, name='tenant-role-list'),
    path(
        'tenants/<uuid:tenant_id>/roles/<uuid:role_id>/',
        role_detail,
        name='tenant-role-detail',
    ),
    path('tenants/<uuid:tenant_id>/users/', user_list, name='tenant-user-list'),
    path(
        'tenants/<uuid:tenant_id>/users/<uuid:user_id>/',
        user_detail,
        name='tenant-user-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/invitation-codes/',
        invitation_list,
        name='tenant-invitation-list',
    ),
    path(
        'tenants/<uuid:tenant_id>/invitation-codes/<uuid:code_id>/',
        invitation_detail,
        name='tenant-invitation-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/integrations/',
        TenantIntegrationsView.as_view(),
        name='tenant-integrations',
    ),
    path(
        'tenants/<uuid:tenant_id>/integrations/google-calendar/',
        GoogleCalendarCredentialView.as_view(),
        name='tenant-google-calendar',
    ),
    path(
        'tenants/<uuid:tenant_id>/integrations/google-calendar/sync/<uuid:reservation_id>/',
        GoogleCalendarSyncTriggerView.as_view(),
        name='tenant-google-calendar-sync',
    ),
]
