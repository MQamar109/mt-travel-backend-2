from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class HotelProperty(TimeStampedModel):
    """Organization-scoped hotel master data (name, address, phone)."""

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.PROTECT,
        related_name='hotel_properties',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=25)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='hotel_properties_created',
    )

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='uniq_hotel_property_name_per_org',
            ),
        ]

    def __str__(self):
        return self.name
