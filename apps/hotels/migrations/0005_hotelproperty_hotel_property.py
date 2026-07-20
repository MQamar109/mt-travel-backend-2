# Generated manually for hotel catalog

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotels', '0004_hotel_organization_alter_hotel_reservation_no_and_more'),
        ('organizations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HotelProperty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('address', models.TextField()),
                ('phone', models.CharField(max_length=25)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='hotel_properties_created', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='hotel_properties', to='organizations.organization')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='hotelproperty',
            constraint=models.UniqueConstraint(fields=('organization', 'name'), name='uniq_hotel_property_name_per_org'),
        ),
        migrations.AddField(
            model_name='hotel',
            name='property',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='bookings', to='hotels.hotelproperty'),
        ),
    ]
