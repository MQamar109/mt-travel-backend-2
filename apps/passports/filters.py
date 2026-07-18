import django_filters
from .models import Passport

class PassportFilter(django_filters.FilterSet):
    issued_date_from = django_filters.DateFilter(field_name='issued_date', lookup_expr='gte')
    issued_date_to = django_filters.DateFilter(field_name='issued_date', lookup_expr='lte')

    class Meta:
        model = Passport
        fields = {
            'payment_type': ['exact'],
            'vendor': ['exact'],
        }
