from rest_framework import serializers
from .models import Hotel
from apps.tickets.utils import get_display_amount


class HotelSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    exchange_rate = serializers.DecimalField(max_digits=8, decimal_places=4, required=True)
    running_balance = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            'id', 'vendor', 'vendor_name', 'created_by', 'created_by_email',
            'guest_name', 'reservation_no', 'hotel_name',
            'issued_date', 'check_in', 'check_out', 'nights',
            'single_qty', 'single_rate', 'double_qty', 'double_rate',
            'triple_qty', 'triple_rate', 'quad_qty', 'quad_rate',
            'meals', 'bf_rate', 'lu_rate', 'di_rate',
            'total_guests', 'total_room_amount', 'total_meal_amount', 'total_amount',
            'running_balance', 'payment_type', 'currency', 'exchange_rate', 'pkr_amount',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_email', 'nights',
            'total_guests', 'total_room_amount', 'total_meal_amount', 'total_amount',
            'running_balance', 'pkr_amount', 'created_at', 'updated_at',
        ]


    def validate_reservation_no(self, value):
        """Unique per organization (replaces the old global unique constraint)."""
        request = self.context.get('request')
        if not request:
            return value
        org_id = getattr(request.user, 'organization_id', None)
        qs = Hotel.objects.filter(organization_id=org_id, reservation_no=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This reservation number already exists in your organization.')
        return value

    def get_running_balance(self, obj):
        balances = self.context.get('running_balances') or {}
        return balances.get(obj.pk)

    def to_representation(self, instance):
        """
        Runtime-only currency conversion (nothing is written to the DB).

        Reads the requested currency from the `currency` query param on the
        request (reliably present in list serializer context, unlike a custom
        context key). When it differs from the record's stored currency, every
        room/meal rate is converted via get_display_amount and the totals are
        recomputed from the converted rates so displayed line items always add
        up to the displayed totals.
        """
        data = super().to_representation(instance)

        request = self.context.get('request')
        display_currency = (
            request.query_params.get('currency', 'PKR').upper() if request else 'PKR'
        )
        record_currency = instance.currency or 'PKR'

        # Same currency → return stored values untouched.
        if display_currency == record_currency:
            return data

        rate = instance.exchange_rate

        def conv(value):
            return get_display_amount(value or 0, record_currency, rate, display_currency)

        # Convert each unit rate.
        single_rate = conv(instance.single_rate)
        double_rate = conv(instance.double_rate)
        triple_rate = conv(instance.triple_rate)
        quad_rate = conv(instance.quad_rate)
        bf_rate = conv(instance.bf_rate)
        lu_rate = conv(instance.lu_rate)
        di_rate = conv(instance.di_rate)

        # Recompute totals from the converted rates (mirrors Hotel.save()).
        nights = instance.nights or 0
        room_total = (
            instance.single_qty * single_rate
            + instance.double_qty * double_rate
            + instance.triple_qty * triple_rate
            + instance.quad_qty * quad_rate
        ) * nights

        if instance.meals and instance.total_guests:
            meal_total = (bf_rate + lu_rate + di_rate) * instance.total_guests * nights
        else:
            meal_total = 0

        grand_total = room_total + meal_total

        # Write converted values back into the serialized payload as strings,
        # matching DRF's DecimalField formatting.
        data['single_rate'] = f'{single_rate:.2f}'
        data['double_rate'] = f'{double_rate:.2f}'
        data['triple_rate'] = f'{triple_rate:.2f}'
        data['quad_rate'] = f'{quad_rate:.2f}'
        data['bf_rate'] = f'{bf_rate:.2f}'
        data['lu_rate'] = f'{lu_rate:.2f}'
        data['di_rate'] = f'{di_rate:.2f}'
        data['total_room_amount'] = f'{room_total:.2f}'
        data['total_meal_amount'] = f'{meal_total:.2f}'
        data['total_amount'] = f'{grand_total:.2f}'

        return data

    def validate(self, data):
        # Only require rates if corresponding qty > 0
        single_qty = data.get('single_qty', 0) or 0
        double_qty = data.get('double_qty', 0) or 0
        triple_qty = data.get('triple_qty', 0) or 0
        quad_qty = data.get('quad_qty', 0) or 0

        if single_qty > 0 and not data.get('single_rate'):
            raise serializers.ValidationError({'single_rate': 'Rate is required when quantity > 0'})
        if double_qty > 0 and not data.get('double_rate'):
            raise serializers.ValidationError({'double_rate': 'Rate is required when quantity > 0'})
        if triple_qty > 0 and not data.get('triple_rate'):
            raise serializers.ValidationError({'triple_rate': 'Rate is required when quantity > 0'})
        if quad_qty > 0 and not data.get('quad_rate'):
            raise serializers.ValidationError({'quad_rate': 'Rate is required when quantity > 0'})

        # Ensure at least one room type
        if single_qty + double_qty + triple_qty + quad_qty == 0:
            raise serializers.ValidationError('At least one room type must have quantity > 0')

        return data
