from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel
from apps.vendors.models import Vendor

CURRENCY_CHOICES = [('PKR', 'PKR'), ('SAR', 'SAR')]
PAYMENT_CHOICES = [('Credit', 'Credit'), ('Debit', 'Debit')]

class Visa(TimeStampedModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.PROTECT,
        related_name='visas',
        null=True,
        blank=True,
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='visas')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='visas')
    invoice_no = models.CharField(max_length=50)
    client_name = models.CharField(max_length=200)
    issued_date = models.DateField(db_index=True)
    visa_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='PKR')
    exchange_rate = models.DecimalField(max_digits=8, decimal_places=4, default=1)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    pkr_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'invoice_no'], name='uniq_visa_invoice_per_org'),
        ]

    def save(self, *args, **kwargs):
        self.total_amount = self.amount
        if self.currency == 'PKR':
            self.pkr_amount = self.total_amount
        else:
            self.pkr_amount = self.total_amount * self.exchange_rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.invoice_no} — {self.client_name}'
