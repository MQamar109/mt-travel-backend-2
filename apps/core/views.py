import datetime

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Chart colours — kept in sync with the frontend mock so recharts renders
# identical slices whether it is fed mock data or the live API.
_CREDIT_COLOR = '#22C55E'
_DEBIT_COLOR  = '#EF4444'
_PKR_COLOR    = '#6366F1'
_SAR_COLOR    = '#F59E0B'

_MONTHS_BACK = 6


def _pkr():
    """
    Fresh expression giving the PKR-equivalent of a record:
    pkr_amount when it is set (SAR records with an exchange rate), otherwise
    total_amount (PKR records, already in rupees).
    A new instance per use avoids Django mutating a shared expression.
    """
    return Coalesce('pkr_amount', 'total_amount')


def _last_months(n=_MONTHS_BACK):
    """Return the last n (year, month) tuples ending with the current month."""
    today = timezone.localdate()
    seq = []
    for i in range(n - 1, -1, -1):
        mm = today.month - i
        yy = today.year
        while mm <= 0:
            mm += 12
            yy -= 1
        seq.append((yy, mm))
    return seq


def _by_month(qs):
    """{(year, month): {'rev': int, 'cnt': int}} keyed by issued_date month."""
    rows = (
        qs
        .annotate(month=TruncMonth('issued_date'))
        .values('month')
        .annotate(rev=Sum(_pkr()), cnt=Count('id'))
    )
    out = {}
    for r in rows:
        if r['month'] is None:
            continue
        out[(r['month'].year, r['month'].month)] = {
            'rev': int(r['rev'] or 0),
            'cnt': r['cnt'] or 0,
        }
    return out


def _vendor_totals(qs):
    """{vendor_id: {'name': str, 'amount': int}} of PKR totals per vendor."""
    rows = (
        qs
        .values('vendor', 'vendor__name')
        .annotate(amt=Sum(_pkr()))
    )
    out = {}
    for r in rows:
        out[r['vendor']] = {
            'name': r['vendor__name'],
            'amount': int(r['amt'] or 0),
        }
    return out


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.vendors.models import Vendor
        from apps.tickets.models import Ticket
        from apps.hotels.models import Hotel
        from apps.core.orgs import org_scoped

        vendors_qs = org_scoped(Vendor.objects.all(), request.user)
        tickets_qs = org_scoped(Ticket.objects.all(), request.user)
        hotels_qs = org_scoped(Hotel.objects.all(), request.user)

        # ── Headline counts ──────────────────────────────────────────────────
        total_vendors = vendors_qs.filter(is_active=True).count()
        total_tickets = tickets_qs.count()
        total_hotels = hotels_qs.count()

        # ── Payment-type aggregates (tickets + hotels, in PKR) ───────────────
        def pay_agg(qs):
            return qs.aggregate(
                credit_count=Count('id', filter=Q(payment_type='Credit')),
                credit_sum=Sum(_pkr(), filter=Q(payment_type='Credit')),
                debit_count=Count('id', filter=Q(payment_type='Debit')),
                debit_sum=Sum(_pkr(), filter=Q(payment_type='Debit')),
            )

        t, h = pay_agg(tickets_qs), pay_agg(hotels_qs)
        credit_count = (t['credit_count'] or 0) + (h['credit_count'] or 0)
        debit_count  = (t['debit_count']  or 0) + (h['debit_count']  or 0)
        credit_sum = int((t['credit_sum'] or 0) + (h['credit_sum'] or 0))
        debit_sum  = int((t['debit_sum']  or 0) + (h['debit_sum']  or 0))
        total_revenue_pkr = credit_sum + debit_sum

        # ── Monthly series (last 6 months, tickets + hotels) ─────────────────
        t_month, h_month = _by_month(tickets_qs), _by_month(hotels_qs)
        revenue_by_month, volume_by_month = [], []
        for (yy, mm) in _last_months():
            label = datetime.date(yy, mm, 1).strftime('%b')
            tm = t_month.get((yy, mm), {})
            hm = h_month.get((yy, mm), {})
            revenue_by_month.append({
                'month': label,
                'revenue': tm.get('rev', 0) + hm.get('rev', 0),
            })
            volume_by_month.append({
                'month': label,
                'tickets': tm.get('cnt', 0),
                'hotels': hm.get('cnt', 0),
            })

        # ── Top 5 vendors by combined PKR revenue ────────────────────────────
        merged = {}
        for vid, info in {**_vendor_totals(tickets_qs)}.items():
            merged[vid] = dict(info)
        for vid, info in _vendor_totals(hotels_qs).items():
            if vid in merged:
                merged[vid]['amount'] += info['amount']
            else:
                merged[vid] = dict(info)
        top_vendors = sorted(merged.values(), key=lambda v: v['amount'], reverse=True)[:5]

        # ── Currency split (record counts) ───────────────────────────────────
        def cur_count(value):
            return (
                tickets_qs.filter(currency=value).count()
                + hotels_qs.filter(currency=value).count()
            )

        currency_split = [
            {'name': 'PKR', 'value': cur_count('PKR'), 'color': _PKR_COLOR},
            {'name': 'SAR', 'value': cur_count('SAR'), 'color': _SAR_COLOR},
        ]

        return Response({
            'totalVendors': total_vendors,
            'totalTickets': total_tickets,
            'totalHotels': total_hotels,
            'totalRevenuePKR': total_revenue_pkr,
            'creditCount': credit_count,
            'creditSum': credit_sum,
            'debitCount': debit_count,
            'debitSum': debit_sum,
            'revenueByMonth': revenue_by_month,
            'volumeByMonth': volume_by_month,
            'paymentSplit': [
                {'name': 'Credit', 'value': credit_count, 'color': _CREDIT_COLOR},
                {'name': 'Debit',  'value': debit_count,  'color': _DEBIT_COLOR},
            ],
            'topVendors': top_vendors,
            'currencySplit': currency_split,
        })
