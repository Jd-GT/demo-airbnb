from django.contrib import admin

from .models import Amenity, Property


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'icon_key')
    search_fields = ('name',)
    list_filter = ('tenant',)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'tenant',
        'capacity_adults',
        'capacity_kids',
        'base_price',
        'cleaning_fee',
    )
    search_fields = ('name', 'address')
    list_filter = ('tenant',)
    filter_horizontal = ('amenities',)
