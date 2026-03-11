from django.urls import path

from .views import AmenityViewSet, PropertyViewSet


amenity_list = AmenityViewSet.as_view({"get": "list", "post": "create"})
amenity_detail = AmenityViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

property_list = PropertyViewSet.as_view({"get": "list", "post": "create"})
property_detail = PropertyViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("tenants/<uuid:tenant_id>/inventory/amenities/", amenity_list, name="amenity-list"),
    path(
        "tenants/<uuid:tenant_id>/inventory/amenities/<uuid:amenity_id>/",
        amenity_detail,
        name="amenity-detail",
    ),
    path("tenants/<uuid:tenant_id>/inventory/properties/", property_list, name="property-list"),
    path(
        "tenants/<uuid:tenant_id>/inventory/properties/<uuid:property_id>/",
        property_detail,
        name="property-detail",
    ),
]
