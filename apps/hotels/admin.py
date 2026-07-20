from django.contrib import admin
from .models import Hotel
from .property_models import HotelProperty


@admin.register(HotelProperty)
class HotelPropertyAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'organization', 'created_at']
    search_fields = ['name', 'address', 'phone']


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['reservation_no', 'hotel_name', 'property', 'guest_name', 'vendor', 'check_in', 'check_out', 'total_amount', 'currency']
    search_fields = ['reservation_no', 'hotel_name', 'guest_name']
    list_filter = ['payment_type', 'currency', 'meals']
