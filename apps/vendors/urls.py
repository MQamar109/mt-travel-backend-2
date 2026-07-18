from django.urls import path
from .views import VendorListCreateView, VendorDetailView

urlpatterns = [
    path('', VendorListCreateView.as_view(), name='vendor-list'),
    path('<int:pk>/', VendorDetailView.as_view(), name='vendor-detail'),
]
