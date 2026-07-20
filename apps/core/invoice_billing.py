from apps.core.company import COMPANY


def _pick(user_value, fallback):
    text = (user_value or '').strip()
    return text if text else fallback


def invoice_billing_for_user(user):
    """
    Bank details for invoice footers: prefer the authenticated user's profile,
    fall back to static COMPANY defaults when fields are empty.
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return dict(COMPANY)

    org = getattr(user, 'organization', None)
    org_name = getattr(org, 'name', None) if org else None
    full_name = user.get_full_name().strip() if hasattr(user, 'get_full_name') else ''
    display_name = org_name or full_name or COMPANY['name']

    return {
        'name': display_name,
        'account_no': _pick(getattr(user, 'account_no', ''), COMPANY['account_no']),
        'bank': _pick(getattr(user, 'bank', ''), COMPANY['bank']),
        'account_name': _pick(getattr(user, 'account_name', ''), COMPANY['account_name']),
    }
