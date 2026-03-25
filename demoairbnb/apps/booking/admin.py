from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'tenant',
        'property',
        'guest',
        'check_in',
        'check_out',
        'status',
        'total_amount',
    )
    list_filter = ('tenant', 'status')
    search_fields = ('property__name', 'guest__name')
