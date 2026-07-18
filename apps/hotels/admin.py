from django.contrib import admin
from .models import Hotel

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ['reservation_no', 'hotel_name', 'guest_name', 'vendor', 'check_in', 'check_out', 'total_amount', 'currency']
    search_fields = ['reservation_no', 'hotel_name', 'guest_name']
    list_filter = ['payment_type', 'currency', 'meals']
