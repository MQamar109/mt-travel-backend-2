from rest_framework import serializers
from .models import Vendor

class VendorSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = Vendor
        fields = [
            'id', 'name', 'short_name', 'company', 'email', 'phone',
            'is_active', 'created_by', 'created_by_email', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_by_email', 'created_at', 'updated_at']

    def _org_id(self):
        request = self.context.get('request')
        return getattr(request.user, 'organization_id', None) if request else None

    def validate_email(self, value):
        """Unique per organization, excluding current vendor on update"""
        queryset = Vendor.objects.filter(organization_id=self._org_id(), email=value)

        # Exclude current vendor when updating
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('A vendor with this email already exists in your organization.')

        return value

    def validate_short_name(self, value):
        """Unique per organization, excluding current vendor on update"""
        queryset = Vendor.objects.filter(organization_id=self._org_id(), short_name=value)

        # Exclude current vendor when updating
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('A vendor with this short name already exists in your organization.')

        return value
