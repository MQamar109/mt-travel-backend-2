from django.contrib import admin
from .models import Visa

@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):
    list_display = ['invoice_no', 'client_name', 'vendor', 'issued_date', 'total_amount', 'currency', 'payment_type']
    search_fields = ['invoice_no', 'client_name', 'visa_number']
    list_filter = ['payment_type', 'currency', 'issued_date']
