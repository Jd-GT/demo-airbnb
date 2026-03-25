from django.urls import path

from .views import AvailabilityCheckView, QuoteView, ReservationViewSet

reservation_list = ReservationViewSet.as_view({'get': 'list', 'post': 'create'})
reservation_detail = ReservationViewSet.as_view({'get': 'retrieve'})

urlpatterns = [
    path(
        'tenants/<uuid:tenant_id>/booking/reservations/',
        reservation_list,
        name='reservation-list',
    ),
    path(
        'tenants/<uuid:tenant_id>/booking/reservations/<uuid:reservation_id>/',
        reservation_detail,
        name='reservation-detail',
    ),
    path(
        'tenants/<uuid:tenant_id>/booking/reservations/availability/',
        AvailabilityCheckView.as_view(),
        name='reservation-availability',
    ),
    path(
        'tenants/<uuid:tenant_id>/booking/quote/',
        QuoteView.as_view(),
        name='booking-quote',
    ),
]
