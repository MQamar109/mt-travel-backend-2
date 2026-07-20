from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.vendors.models import Vendor
from .property_models import HotelProperty

CURRENCY_CHOICES = [('PKR', 'PKR'), ('SAR', 'SAR')]
PAYMENT_CHOICES = [('Credit', 'Credit'), ('Debit', 'Debit')]

class Hotel(TimeStampedModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.PROTECT,
        related_name='hotels',
        null=True,
        blank=True,
    )
    property = models.ForeignKey(
        HotelProperty,
        on_delete=models.PROTECT,
        related_name='bookings',
        null=True,
        blank=True,
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='hotels')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='hotels')
    guest_name = models.CharField(max_length=200)
    reservation_no = models.CharField(max_length=50)
    hotel_name = models.CharField(max_length=200)
    issued_date = models.DateField(db_index=True)
    check_in = models.DateField(db_index=True)
    check_out = models.DateField()
    nights = models.PositiveSmallIntegerField(default=0)
    single_qty = models.PositiveSmallIntegerField(default=0)
    single_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    double_qty = models.PositiveSmallIntegerField(default=0)
    double_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    triple_qty = models.PositiveSmallIntegerField(default=0)
    triple_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quad_qty = models.PositiveSmallIntegerField(default=0)
    quad_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    meals = models.BooleanField(default=False)
    bf_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    lu_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    di_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    total_guests = models.PositiveSmallIntegerField(default=0)
    total_room_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_meal_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='PKR')
    exchange_rate = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    pkr_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'reservation_no'], name='uniq_hotel_reservation_per_org'),
        ]

    def save(self, *args, **kwargs):
        if self.property_id and self.property:
            self.hotel_name = self.property.name
        if self.check_in and self.check_out:
            self.nights = (self.check_out - self.check_in).days
        self.total_guests = (
            self.single_qty +
            self.double_qty * 2 +
            self.triple_qty * 3 +
            self.quad_qty * 4
        )
        self.total_room_amount = (
            self.single_qty * self.single_rate +
            self.double_qty * self.double_rate +
            self.triple_qty * self.triple_rate +
            self.quad_qty * self.quad_rate
        ) * self.nights
        if self.meals and self.total_guests:
            meal_per_person = (
                (self.bf_rate or 0) +
                (self.lu_rate or 0) +
                (self.di_rate or 0)
            )
            self.total_meal_amount = meal_per_person * self.total_guests * self.nights
        else:
            self.total_meal_amount = 0
        self.total_amount = self.total_room_amount + self.total_meal_amount
        if self.currency == 'PKR':
            self.pkr_amount = self.total_amount
        else:
            self.pkr_amount = self.total_amount * self.exchange_rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.reservation_no} — {self.hotel_name}'
