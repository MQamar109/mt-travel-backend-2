from django.contrib import admin
from .models import Passport

@admin.register(Passport)
class PassportAdmin(admin.ModelAdmin):
    list_display = ['invoice_no', 'client_name', 'vendor', 'issued_date', 'total_amount', 'currency', 'payment_type']
    search_fields = ['invoice_no', 'client_name', 'passport_number']
    list_filter = ['payment_type', 'currency', 'issued_date']
