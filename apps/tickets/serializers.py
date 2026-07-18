from rest_framework import serializers
from .models import Ticket
from .utils import get_display_amount


class TicketSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    exchange_rate = serializers.DecimalField(max_digits=8, decimal_places=4, required=True)
    display_amount = serializers.SerializerMethodField()
    running_balance = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'vendor', 'vendor_name', 'created_by', 'created_by_email',
            'invoice_no', 'customer_name', 'issued_date', 'departure_date',
            'adt_qty', 'adt_rate', 'chd_qty', 'chd_rate', 'inf_qty', 'inf_rate',
            'no_of_tickets', 'total_amount', 'display_amount', 'running_balance', 'description',
            'payment_type', 'currency', 'exchange_rate', 'pkr_amount',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_email',
            'no_of_tickets', 'total_amount', 'display_amount', 'running_balance', 'pkr_amount',
            'created_at', 'updated_at',
        ]


    def validate_invoice_no(self, value):
        """Unique per organization (replaces the old global unique constraint)."""
        request = self.context.get('request')
        if not request:
            return value
        org_id = getattr(request.user, 'organization_id', None)
        qs = Ticket.objects.filter(organization_id=org_id, invoice_no=value)
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

        Reads the requested currency from the `currency` query param (reliably
        present in list serializer context). When it differs from the record's
        stored currency, each ticket-type rate is converted via
        get_display_amount and total_amount is recomputed from the converted
        rates so line items always add up to the total. Records already in the
        requested currency pass through untouched.
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

        def conv(value):
            return get_display_amount(value or 0, record_currency, rate, display_currency)

        adt_rate = conv(instance.adt_rate)
        chd_rate = conv(instance.chd_rate)
        inf_rate = conv(instance.inf_rate)

        # Recompute total from the converted rates (mirrors Ticket.save()).
        total = (
            instance.adt_qty * adt_rate
            + instance.chd_qty * chd_rate
            + instance.inf_qty * inf_rate
        )

        data['adt_rate'] = f'{adt_rate:.2f}'
        data['chd_rate'] = f'{chd_rate:.2f}'
        data['inf_rate'] = f'{inf_rate:.2f}'
        data['total_amount'] = f'{total:.2f}'
        # Keep display_amount consistent with the recomputed total.
        data['display_amount'] = total

        return data

    def validate(self, data):
        # Only require rates if corresponding qty > 0
        adt_qty = data.get('adt_qty', 0) or 0
        chd_qty = data.get('chd_qty', 0) or 0
        inf_qty = data.get('inf_qty', 0) or 0

        if adt_qty > 0 and not data.get('adt_rate'):
            raise serializers.ValidationError({'adt_rate': 'Rate is required when quantity > 0'})
        if chd_qty > 0 and not data.get('chd_rate'):
            raise serializers.ValidationError({'chd_rate': 'Rate is required when quantity > 0'})
        if inf_qty > 0 and not data.get('inf_rate'):
            raise serializers.ValidationError({'inf_rate': 'Rate is required when quantity > 0'})

        # Ensure at least one ticket type
        if adt_qty + chd_qty + inf_qty == 0:
            raise serializers.ValidationError('At least one ticket type must have quantity > 0')

        return data
