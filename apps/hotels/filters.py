import django_filters
from .models import Hotel

class HotelFilter(django_filters.FilterSet):
    issued_date_from = django_filters.DateFilter(field_name='issued_date', lookup_expr='gte')
    issued_date_to = django_filters.DateFilter(field_name='issued_date', lookup_expr='lte')
    check_in_from = django_filters.DateFilter(field_name='check_in', lookup_expr='gte')
    check_in_to = django_filters.DateFilter(field_name='check_in', lookup_expr='lte')

    class Meta:
        model = Hotel
        fields = {
            'payment_type': ['exact'],
            'vendor': ['exact'],
        }
