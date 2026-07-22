from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Case, DecimalField, F, Value, When
from django.db.models.functions import Coalesce

_AMOUNT_OUTPUT = DecimalField(max_digits=14, decimal_places=2)


def get_display_amount(total_amount, record_currency, exchange_rate, display_currency):
    """
    Returns the amount converted to display_currency.
    - display_currency=PKR: PKR records as-is, SAR records * exchange_rate
    - display_currency=SAR: SAR records as-is, PKR records / exchange_rate
    """
    total = Decimal(str(total_amount))
    rate = Decimal(str(exchange_rate)) if exchange_rate else Decimal('1')

    if display_currency == 'PKR':
        if record_currency == 'PKR':
            return total
        return total * rate
    else:  # SAR
        if record_currency == 'SAR':
            return total
        return (total / rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if rate else total


def display_amount_expression(display_currency):
    """
    ORM expression for aggregating record amounts in the requested currency.
    PKR: Coalesce(pkr_amount, total_amount)
    SAR: SAR records as-is; PKR records divided by exchange_rate
    """
    if display_currency == 'PKR':
        return Coalesce(F('pkr_amount'), F('total_amount'), output_field=_AMOUNT_OUTPUT)

    safe_rate = Coalesce(F('exchange_rate'), Value(1), output_field=_AMOUNT_OUTPUT)

    return Case(
        When(currency='SAR', then=F('total_amount')),
        When(currency='PKR', then=F('total_amount') / safe_rate),
        default=F('total_amount'),
        output_field=_AMOUNT_OUTPUT,
    )


def aggregate_display_amount_stats(queryset, display_currency, date_field='issued_date'):
    """Aggregate counts and sums in the requested display currency."""
    from django.db.models import Count, Sum
    from django.utils import timezone

    annotated = queryset.annotate(
        display_amount=display_amount_expression(display_currency)
    )

    total_count = annotated.count()
    total_amount = annotated.aggregate(total=Sum('display_amount'))['total'] or 0

    credit_stats = annotated.filter(payment_type='Credit').aggregate(
        count=Count('id'),
        amount=Sum('display_amount'),
    )
    debit_stats = annotated.filter(payment_type='Debit').aggregate(
        count=Count('id'),
        amount=Sum('display_amount'),
    )

    now = timezone.now()
    this_month_count = annotated.filter(
        **{f'{date_field}__month': now.month, f'{date_field}__year': now.year}
    ).count()

    return {
        'totalCount': total_count,
        'totalAmount': int(total_amount),
        'creditCount': credit_stats['count'] or 0,
        'creditAmount': int(credit_stats['amount'] or 0),
        'debitCount': debit_stats['count'] or 0,
        'debitAmount': int(debit_stats['amount'] or 0),
        'thisMonthCount': this_month_count,
        'displayCurrency': display_currency,
    }
