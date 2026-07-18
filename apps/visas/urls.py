from django.urls import path
from .views import (
    VisaListCreateView, VisaDetailView,
    VisaExportView, VisaEmailView,
    VisaInvoiceView, VisaInvoiceEmailView,
    VisaStatsView,
)

urlpatterns = [
    path('', VisaListCreateView.as_view(), name='visa-list'),
    path('stats/', VisaStatsView.as_view(), name='visa-stats'),
    path('export/', VisaExportView.as_view(), name='visa-export'),
    path('email/', VisaEmailView.as_view(), name='visa-email'),
    path('<int:pk>/', VisaDetailView.as_view(), name='visa-detail'),
    path('<int:pk>/invoice/', VisaInvoiceView.as_view(), name='visa-invoice'),
    path('<int:pk>/invoice/email/', VisaInvoiceEmailView.as_view(), name='visa-invoice-email'),
]
