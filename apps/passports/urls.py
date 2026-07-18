from django.urls import path
from .views import (
    PassportListCreateView, PassportDetailView,
    PassportExportView, PassportEmailView,
    PassportInvoiceView, PassportInvoiceEmailView,
    PassportStatsView,
)

urlpatterns = [
    path('', PassportListCreateView.as_view(), name='passport-list'),
    path('stats/', PassportStatsView.as_view(), name='passport-stats'),
    path('export/', PassportExportView.as_view(), name='passport-export'),
    path('email/', PassportEmailView.as_view(), name='passport-email'),
    path('<int:pk>/', PassportDetailView.as_view(), name='passport-detail'),
    path('<int:pk>/invoice/', PassportInvoiceView.as_view(), name='passport-invoice'),
    path('<int:pk>/invoice/email/', PassportInvoiceEmailView.as_view(), name='passport-invoice-email'),
]
