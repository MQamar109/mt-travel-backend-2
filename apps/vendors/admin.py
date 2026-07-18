from django.contrib import admin
from .models import Vendor

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'company', 'email', 'is_active', 'created_at']
    search_fields = ['name', 'company', 'email']
    list_filter = ['is_active']
