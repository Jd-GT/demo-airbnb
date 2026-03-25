from django.urls import path

from .views import ContactViewSet, LeadViewSet

contact_list = ContactViewSet.as_view({'get': 'list', 'post': 'create'})
contact_detail = ContactViewSet.as_view(
    {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}
)

lead_list = LeadViewSet.as_view({'get': 'list', 'post': 'create'})
lead_detail = LeadViewSet.as_view(
    {'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}
)

urlpatterns = [
    path('tenants/<uuid:tenant_id>/crm/contacts/', contact_list, name='contact-list'),
    path(
        'tenants/<uuid:tenant_id>/crm/contacts/<uuid:contact_id>/',
        contact_detail,
        name='contact-detail',
    ),
    path('tenants/<uuid:tenant_id>/crm/leads/', lead_list, name='lead-list'),
    path(
        'tenants/<uuid:tenant_id>/crm/leads/<uuid:lead_id>/',
        lead_detail,
        name='lead-detail',
    ),
]
