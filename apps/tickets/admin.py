from django.contrib import admin
from .models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['invoice_no', 'customer_name', 'vendor', 'issued_date', 'total_amount', 'currency', 'payment_type']
    search_fields = ['invoice_no', 'customer_name']
    list_filter = ['payment_type', 'currency', 'issued_date']
