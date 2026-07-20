from django.urls import path
from .views import (
    HotelListCreateView, HotelDetailView,
    HotelExportView, HotelEmailView,
    HotelInvoiceView, HotelInvoiceEmailView,
    HotelStatsView,
)
from .property_views import HotelPropertyListCreateView, HotelPropertyDetailView

urlpatterns = [
    path('properties/', HotelPropertyListCreateView.as_view(), name='hotel-property-list'),
    path('properties/<int:pk>/', HotelPropertyDetailView.as_view(), name='hotel-property-detail'),
    path('', HotelListCreateView.as_view(), name='hotel-list'),
    path('stats/', HotelStatsView.as_view(), name='hotel-stats'),
    path('export/', HotelExportView.as_view(), name='hotel-export'),
    path('email/', HotelEmailView.as_view(), name='hotel-email'),
    path('<int:pk>/', HotelDetailView.as_view(), name='hotel-detail'),
    path('<int:pk>/invoice/', HotelInvoiceView.as_view(), name='hotel-invoice'),
    path('<int:pk>/invoice/email/', HotelInvoiceEmailView.as_view(), name='hotel-invoice-email'),
]
