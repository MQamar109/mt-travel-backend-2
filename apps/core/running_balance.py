from decimal import Decimal

from apps.core.currency import get_display_amount


def get_list_display_amount(record, display_currency):
    """Converted row amount used for running balance (runtime only, not stored)."""
    return get_display_amount(
        record.total_amount,
        record.currency or 'PKR',
        record.exchange_rate,
        display_currency,
    )


def apply_balance_step(running_balance, payment_type, amount):
    """
    Credit adds, Debit subtracts.
    First row: Credit starts positive, Debit starts negative.
    """
    amount = Decimal(str(amount))

    if running_balance is None:
        return amount if payment_type == 'Credit' else -amount

    if payment_type == 'Credit':
        return running_balance + amount
    return running_balance - amount


def build_running_balances(records, display_currency, get_amount=None):
    """
    Walk records in created_at order and return {pk: running_balance}.
    Nothing is persisted — computed in memory when building the response.
    """
    amount_fn = get_amount or get_list_display_amount
    balances = {}
    running = None

    for record in records:
        amount = amount_fn(record, display_currency)
        running = apply_balance_step(running, record.payment_type, amount)
        balances[record.pk] = float(running)

    return balances
