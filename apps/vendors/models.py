from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel

class Vendor(TimeStampedModel):
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.PROTECT,
        related_name='vendors',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=10)
    company = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=25)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='vendors',
    )

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'short_name'], name='uniq_vendor_shortname_per_org'),
            models.UniqueConstraint(fields=['organization', 'email'], name='uniq_vendor_email_per_org'),
        ]

    def __str__(self):
        return f'{self.short_name} — {self.name}'
