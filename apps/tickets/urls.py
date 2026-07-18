from django.urls import path
from .views import (
    TicketListCreateView, TicketDetailView,
    TicketExportView, TicketEmailView,
    TicketInvoiceView, TicketInvoiceEmailView,
    TicketStatsView,
)

urlpatterns = [
    path('', TicketListCreateView.as_view(), name='ticket-list'),
    path('stats/', TicketStatsView.as_view(), name='ticket-stats'),
    path('export/', TicketExportView.as_view(), name='ticket-export'),
    path('email/', TicketEmailView.as_view(), name='ticket-email'),
    path('<int:pk>/', TicketDetailView.as_view(), name='ticket-detail'),
    path('<int:pk>/invoice/', TicketInvoiceView.as_view(), name='ticket-invoice'),
    path('<int:pk>/invoice/email/', TicketInvoiceEmailView.as_view(), name='ticket-invoice-email'),
]
