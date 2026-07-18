from rest_framework import serializers
from apps.tickets.utils import get_display_amount
from .models import Passport


class PassportSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    exchange_rate = serializers.DecimalField(max_digits=8, decimal_places=4, required=True)
    display_amount = serializers.SerializerMethodField()
    running_balance = serializers.SerializerMethodField()

    class Meta:
        model = Passport
        fields = [
            'id', 'vendor', 'vendor_name', 'created_by', 'created_by_email',
            'invoice_no', 'client_name', 'issued_date', 'passport_number',
            'description', 'amount', 'total_amount', 'display_amount', 'running_balance',
            'payment_type', 'currency', 'exchange_rate', 'pkr_amount',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_email',
            'total_amount', 'display_amount', 'running_balance', 'pkr_amount',
            'created_at', 'updated_at',
        ]


    def validate_invoice_no(self, value):
        """Unique per organization (replaces the old global unique constraint)."""
        request = self.context.get('request')
        if not request:
            return value
        org_id = getattr(request.user, 'organization_id', None)
        qs = Passport.objects.filter(organization_id=org_id, invoice_no=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This invoice number already exists in your organization.')
        return value

    def get_display_amount(self, obj):
        request = self.context.get('request')
        display_currency = 'PKR'
        if request:
            display_currency = request.query_params.get('currency', 'PKR').upper()
        return get_display_amount(obj.total_amount, obj.currency, obj.exchange_rate, display_currency)

    def get_running_balance(self, obj):
        balances = self.context.get('running_balances') or {}
        return balances.get(obj.pk)

    def to_representation(self, instance):
        """
        Runtime-only currency conversion (nothing is written to the DB).
        When the requested display currency differs from the record's stored
        currency, amount/total_amount are converted via get_display_amount.
        """
        data = super().to_representation(instance)

        request = self.context.get('request')
        display_currency = (
            request.query_params.get('currency', 'PKR').upper() if request else 'PKR'
        )
        record_currency = instance.currency or 'PKR'

        if display_currency == record_currency:
            return data

        rate = instance.exchange_rate
        amount = get_display_amount(instance.amount or 0, record_currency, rate, display_currency)

        data['amount'] = f'{amount:.2f}'
        data['total_amount'] = f'{amount:.2f}'
        data['display_amount'] = amount

        return data

    def validate_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('Amount must be greater than 0')
        return value
