from apps.core.running_balance import build_running_balances


class RunningBalanceListMixin:
    """Attach per-row running_balance to paginated list responses."""

    balance_ordering = ('created_at', 'id')

    def get_queryset(self):
        return super().get_queryset().order_by(*self.balance_ordering)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        display_currency = request.query_params.get('currency', 'PKR').upper()

        self._running_balances = build_running_balances(
            queryset.order_by(*self.balance_ordering).iterator(),
            display_currency,
        )
        return super().list(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if hasattr(self, '_running_balances'):
            context['running_balances'] = self._running_balances
        return context
