import django_filters
from .models import Visa

class VisaFilter(django_filters.FilterSet):
    issued_date_from = django_filters.DateFilter(field_name='issued_date', lookup_expr='gte')
    issued_date_to = django_filters.DateFilter(field_name='issued_date', lookup_expr='lte')

    class Meta:
        model = Visa
        fields = {
            'payment_type': ['exact'],
            'vendor': ['exact'],
        }
