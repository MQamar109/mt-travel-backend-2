"""
Assign all existing users and domain records to a Default Organization so
nothing disappears when organization-based data isolation turns on.
"""
from django.db import migrations

DEFAULT_ORG_NAME = 'Default Organization'


def assign_default_org(apps, schema_editor):
    Organization = apps.get_model('organizations', 'Organization')
    org, _ = Organization.objects.get_or_create(name=DEFAULT_ORG_NAME)

    models = [
        ('users', 'CustomUser'),
        ('vendors', 'Vendor'),
        ('tickets', 'Ticket'),
        ('hotels', 'Hotel'),
        ('visas', 'Visa'),
        ('passports', 'Passport'),
    ]
    for app_label, model_name in models:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(organization__isnull=True).update(organization=org)


def unassign_default_org(apps, schema_editor):
    Organization = apps.get_model('organizations', 'Organization')
    org = Organization.objects.filter(name=DEFAULT_ORG_NAME).first()
    if not org:
        return
    models = [
        ('users', 'CustomUser'),
        ('vendors', 'Vendor'),
        ('tickets', 'Ticket'),
        ('hotels', 'Hotel'),
        ('visas', 'Visa'),
        ('passports', 'Passport'),
    ]
    for app_label, model_name in models:
        Model = apps.get_model(app_label, model_name)
        Model.objects.filter(organization=org).update(organization=None)


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('users', '0002_customuser_organization'),
        ('vendors', '0003_vendor_organization_alter_vendor_email_and_more'),
        ('tickets', '0004_ticket_organization_alter_ticket_invoice_no_and_more'),
        ('hotels', '0004_hotel_organization_alter_hotel_reservation_no_and_more'),
        ('visas', '0002_visa_organization_alter_visa_invoice_no_and_more'),
        ('passports', '0002_passport_organization_alter_passport_invoice_no_and_more'),
    ]

    operations = [
        migrations.RunPython(assign_default_org, unassign_default_org),
    ]
