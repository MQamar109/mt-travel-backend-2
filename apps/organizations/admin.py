from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Organization


class UserInline(admin.TabularInline):
    model = get_user_model()
    fields = ['email', 'first_name', 'last_name', 'role', 'is_active']
    readonly_fields = ['email', 'first_name', 'last_name']
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'user_count', 'created_at']
    search_fields = ['name']
    list_filter = ['is_active']
    inlines = [UserInline]

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Users'
