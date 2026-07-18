from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.permissions import IsAdminRole
from apps.core.orgs import org_scoped, require_organization
from apps.core.email_utils import send_in_background
from apps.core.currency import aggregate_display_amount_stats
from apps.core.mixins import RunningBalanceListMixin
from .models import Ticket
from .serializers import TicketSerializer
from .filters import TicketFilter
from .exports import generate_excel, generate_pdf
from .email_report import send_ticket_report
from .invoice import generate_ticket_invoice


class TicketListCreateView(RunningBalanceListMixin, ListCreateAPIView):
    serializer_class = TicketSerializer
    filterset_class = TicketFilter
    search_fields = ['customer_name', 'invoice_no', 'vendor__name']
    ordering_fields = ['issued_date', 'departure_date', 'total_amount', 'created_at']

    def get_queryset(self):
        return org_scoped(Ticket.objects.select_related('vendor', 'created_by'), self.request.user)

    def perform_create(self, serializer):
        require_organization(self.request.user)
        serializer.save(created_by=self.request.user, organization_id=self.request.user.organization_id)


class TicketDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = TicketSerializer

    def get_queryset(self):
        return org_scoped(Ticket.objects.select_related('vendor', 'created_by'), self.request.user)

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdminRole()]
        return [IsAuthenticated()]


class TicketExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        export_format = request.query_params.get('file_format', 'excel').lower()
        display_currency = request.query_params.get('currency', 'PKR').upper()

        # Apply same filters as list view
        from .filters import TicketFilter
        queryset = org_scoped(Ticket.objects.select_related('vendor', 'created_by'), request.user)
        filtered = TicketFilter(request.query_params, queryset=queryset).qs.order_by('created_at', 'id')

        # Build meta for title block
        date_from = request.query_params.get('issued_date_from', '')
        date_to = request.query_params.get('issued_date_to', '')
        if date_from and date_to:
            duration = f'{date_from} to {date_to}'
        elif date_from:
            duration = f'From {date_from}'
        elif date_to:
            duration = f'Until {date_to}'
        else:
            duration = 'All Dates'

        vendor_id = request.query_params.get('vendor')
        vendor_name = None
        if vendor_id:
            from apps.vendors.models import Vendor
            try:
                vendor_name = Vendor.objects.get(pk=vendor_id).name
            except Vendor.DoesNotExist:
                pass

        meta = {'duration': duration, 'vendor_name': vendor_name}

        optional_columns_raw = request.query_params.get('optional_columns', '')
        optional_columns = {c.strip().lower() for c in optional_columns_raw.split(',') if c.strip()}
        options = {
            'show_vendor': 'vendor' in optional_columns,
            'show_dep_date': 'dep_date' in optional_columns,
            'show_tickets_count': 'no_of_tickets' in optional_columns,
        }

        if export_format == 'pdf':
            buffer = generate_pdf(filtered.iterator(), display_currency, meta, options)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="tickets_report.pdf"'
        else:
            buffer = generate_excel(filtered.iterator(), display_currency, meta, options)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            response['Content-Disposition'] = 'attachment; filename="tickets_report.xlsx"'

        return response


def _build_ticket_meta(request):
    date_from = request.query_params.get('issued_date_from', '')
    date_to = request.query_params.get('issued_date_to', '')
    if date_from and date_to:
        duration = f'{date_from} to {date_to}'
    elif date_from:
        duration = f'From {date_from}'
    elif date_to:
        duration = f'Until {date_to}'
    else:
        duration = 'All Dates'

    vendor_id = request.query_params.get('vendor')
    vendor_name = None
    if vendor_id:
        from apps.vendors.models import Vendor
        try:
            vendor_name = Vendor.objects.get(pk=vendor_id).name
        except Vendor.DoesNotExist:
            pass

    return {'duration': duration, 'vendor_name': vendor_name}


class TicketEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        to_email = request.query_params.get('email', '').strip()
        if not to_email:
            return Response({'detail': 'email parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(to_email)
        except ValidationError:
            return Response({'detail': f'"{to_email}" is not a valid email address.'}, status=status.HTTP_400_BAD_REQUEST)

        display_currency = request.query_params.get('currency', 'PKR').upper()
        queryset = org_scoped(Ticket.objects.select_related('vendor', 'created_by'), request.user)
        filtered = TicketFilter(request.query_params, queryset=queryset).qs.order_by('created_at', 'id')
        meta = _build_ticket_meta(request)

        optional_columns_raw = request.query_params.get('optional_columns', '')
        optional_columns = {c.strip().lower() for c in optional_columns_raw.split(',') if c.strip()}
        options = {
            'show_vendor': 'vendor' in optional_columns,
            'show_dep_date': 'dep_date' in optional_columns,
            'show_tickets_count': 'no_of_tickets' in optional_columns,
        }

        # Materialise the queryset now, then send in a background thread so the
        # API responds immediately instead of blocking on SMTP.
        records = list(filtered)
        send_in_background(send_ticket_report, to_email, records, display_currency, meta, options)

        return Response({'detail': f'Ticket report is being sent to {to_email}.'})


def _parse_optional(request):
    raw = request.query_params.get('optional', '')
    return {f.strip().lower() for f in raw.split(',') if f.strip()}


class TicketInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ticket = org_scoped(Ticket.objects.select_related('vendor'), request.user).filter(pk=pk).first()
        if not ticket:
            return Response({'detail': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        display_currency = request.query_params.get('currency', 'PKR').upper()
        optional_fields = _parse_optional(request)

        buf = generate_ticket_invoice(ticket, display_currency, optional_fields)
        response = HttpResponse(buf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{ticket.invoice_no}.pdf"'
        return response


class TicketInvoiceEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ticket = org_scoped(Ticket.objects.select_related('vendor'), request.user).filter(pk=pk).first()
        if not ticket:
            return Response({'detail': 'Ticket not found.'}, status=status.HTTP_404_NOT_FOUND)

        to_email = request.query_params.get('email', '').strip()
        if not to_email:
            return Response({'detail': 'email parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_email(to_email)
        except ValidationError:
            return Response({'detail': f'"{to_email}" is not a valid email address.'}, status=status.HTTP_400_BAD_REQUEST)

        display_currency = request.query_params.get('currency', 'PKR').upper()
        optional_fields = _parse_optional(request)

        try:
            from django.conf import settings as django_settings
            from django.core.mail import EmailMessage
            buf = generate_ticket_invoice(ticket, display_currency, optional_fields)
            email = EmailMessage(
                subject=f'Invoice {ticket.invoice_no} – {ticket.customer_name}',
                body='Please find your invoice attached.',
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            email.attach(f'invoice_{ticket.invoice_no}.pdf', buf.read(), 'application/pdf')
            send_in_background(email.send, fail_silently=False)
        except Exception as exc:
            return Response({'detail': f'Failed to send email: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'detail': f'Invoice {ticket.invoice_no} is being sent to {to_email}.'})


class TicketStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = org_scoped(Ticket.objects.select_related('vendor', 'created_by'), request.user)
        filtered = TicketFilter(request.query_params, queryset=queryset).qs.order_by('created_at', 'id')
        display_currency = request.query_params.get('currency', 'PKR').upper()

        return Response(aggregate_display_amount_stats(filtered, display_currency))
