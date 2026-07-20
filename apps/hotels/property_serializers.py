from rest_framework import serializers

from .property_models import HotelProperty


class HotelPropertySerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    bookings_count = serializers.SerializerMethodField()

    class Meta:
        model = HotelProperty
        fields = [
            'id', 'name', 'address', 'phone',
            'created_by', 'created_by_email', 'bookings_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_by_email', 'bookings_count', 'created_at', 'updated_at']

    def get_bookings_count(self, obj):
        return obj.bookings.count()

    def _org_id(self):
        request = self.context.get('request')
        return getattr(request.user, 'organization_id', None) if request else None

    def validate_name(self, value):
        org_id = self._org_id()
        if not org_id:
            return value
        qs = HotelProperty.objects.filter(organization_id=org_id, name__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'A hotel with this name already exists in your organization.'
            )
        return value.strip()
