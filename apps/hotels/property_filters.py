import django_filters

from .property_models import HotelProperty


class HotelPropertyFilter(django_filters.FilterSet):
    class Meta:
        model = HotelProperty
        fields = {}
