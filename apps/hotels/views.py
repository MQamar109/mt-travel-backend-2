from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Sum
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
from .models import Hotel
from .serializers import HotelSerializer
from .filters import HotelFilter
from .exports import generate_excel, generate_pdf
from .email_report import send_hotel_report
from .invoice import generate_hotel_invoice

class HotelListCreateView(RunningBalanceListMixin, ListCreateAPIView):
    serializer_class = HotelSerializer
    filterset_class = HotelFilter
    search_fields = ['guest_name', 'hotel_name', 'reservation_no', 'vendor__name', 'property__name']
    ordering_fields = ['issued_date', 'check_in', 'total_amount', 'created_at']

    def get_queryset(self):
        return org_scoped(
            Hotel.objects.select_related('vendor', 'created_by', 'property'),
            self.request.user,
        )

    def perform_create(self, serializer):
        require_organization(self.request.user)
        serializer.save(created_by=self.request.user, organization_id=self.request.user.organization_id)


class HotelDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = HotelSerializer

    def get_queryset(self):
        return org_scoped(
            Hotel.objects.select_related('vendor', 'created_by', 'property'),
            self.request.user,
        )

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdminRole()]
        return [IsAuthenticated()]


class HotelExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        export_format = request.query_params.get('file_format', 'excel').lower()
        display_currency = request.query_params.get('currency', 'PKR').upper()

        queryset = org_scoped(Hotel.objects.select_related('vendor', 'created_by'), request.user)
        filtered = HotelFilter(request.query_params, queryset=queryset).qs.order_by('created_at', 'id')

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

        if export_format == 'pdf':
            buffer = generate_pdf(filtered.iterator(), display_currency, meta)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="hotels_report.pdf"'
        else:
            buffer = generate_excel(filtered.iterator(), display_currency, meta)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            response['Content-Disposition'] = 'attachment; filename="hotels_report.xlsx"'

        return response


def _build_hotel_meta(request):
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


class HotelEmailView(APIView):
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
        queryset = org_scoped(Hotel.objects.select_related('vendor', 'created_by'), request.user)
        filtered = HotelFilter(request.query_params, queryset=queryset).qs.order_by('created_at', 'id')
        meta = _build_hotel_meta(request)

        # Materialise the queryset now, then send in a background thread so the
        # API responds immediately instead of blocking on SMTP.
        records = list(filtered)
        send_in_background(send_hotel_report, to_email, records, display_currency, meta)

        return Response({'detail': f'Hotel report is being sent to {to_email}.'})


def _parse_optional(request):
    raw = request.query_params.get('optional', '')
    return {f.strip().lower() for f in raw.split(',') if f.strip()}


class HotelInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        hotel = org_scoped(Hotel.objects.select_related('vendor'), request.user).filter(pk=pk).first()
        if not hotel:
            return Response({'detail': 'Hotel record not found.'}, status=status.HTTP_404_NOT_FOUND)

        display_currency = request.query_params.get('currency', 'PKR').upper()
        optional_fields = _parse_optional(request)

        buf = generate_hotel_invoice(hotel, display_currency, optional_fields)
        response = HttpResponse(buf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{hotel.reservation_no}.pdf"'
        return response


class HotelInvoiceEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        hotel = org_scoped(Hotel.objects.select_related('vendor'), request.user).filter(pk=pk).first()
        if not hotel:
            return Response({'detail': 'Hotel record not found.'}, status=status.HTTP_404_NOT_FOUND)

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
            buf = generate_hotel_invoice(hotel, display_currency, optional_fields)
            email = EmailMessage(
                subject=f'Invoice {hotel.reservation_no} – {hotel.guest_name}',
                body='Please find your invoice attached.',
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
            )
            email.attach(f'invoice_{hotel.reservation_no}.pdf', buf.read(), 'application/pdf')
            send_in_background(email.send, fail_silently=False)
        except Exception as exc:
            return Response({'detail': f'Failed to send email: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'detail': f'Invoice {hotel.reservation_no} sent to {to_email}.'})


class HotelStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = org_scoped(Hotel.objects.select_related('vendor', 'created_by'), request.user)
        filtered = HotelFilter(request.query_params, queryset=queryset).qs.order_by('created_at', 'id')
        display_currency = request.query_params.get('currency', 'PKR').upper()

        return Response(
            aggregate_display_amount_stats(filtered, display_currency, date_field='check_in')
        )
