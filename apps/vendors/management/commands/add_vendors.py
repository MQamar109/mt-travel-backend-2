from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.vendors.models import Vendor

User = get_user_model()

VENDOR_DATA = [
    ("Ahmad Travel", "AHM", "Ahmad Travels Pvt Ltd", "ahmad@travels.pk", "+92-300-1234567"),
    ("Karachi Tours", "KAR", "Karachi Tour Services", "info@karachitours.pk", "+92-301-2345678"),
    ("Islamabad Voyage", "ISB", "Islamabad Voyage Company", "contact@ibdvoyage.pk", "+92-302-3456789"),
    ("Lahore Adventures", "LAH", "Lahore Adventures Inc", "admin@lahoreadv.pk", "+92-303-4567890"),
    ("Peshawar Journeys", "PES", "Peshawar Journey Makers", "info@pesjourneys.pk", "+92-304-5678901"),
    ("Quetta Explorers", "QUE", "Quetta Explorers Ltd", "contact@quettaexp.pk", "+92-305-6789012"),
    ("Multan Tours", "MUL", "Multan Tour Agency", "tours@multantours.pk", "+92-306-7890123"),
    ("Faisalabad Travels", "FAI", "Faisalabad Travel Group", "admin@faisalbadtravel.pk", "+92-307-8901234"),
    ("Sialkot Voyages", "SIA", "Sialkot Voyage Ltd", "contact@sialkotv.pk", "+92-308-9012345"),
    ("Gujranwala Tours", "GUJ", "Gujranwala Tours Inc", "info@gujrantours.pk", "+92-309-0123456"),
    ("Rawalpindi Adventures", "RAW", "Rawalpindi Adventure Co", "admin@rawadventure.pk", "+92-310-1234567"),
    ("Bahawalpur Journeys", "BAH", "Bahawalpur Journey Services", "contact@bahjourneys.pk", "+92-311-2345678"),
    ("Gilgit Expeditions", "GIL", "Gilgit Expedition Ltd", "info@gilgitexp.pk", "+92-312-3456789"),
    ("Skardu Travels", "SKA", "Skardu Travel Company", "admin@skardutrav.pk", "+92-313-4567890"),
    ("Swat Valley Tours", "SWA", "Swat Valley Tour Ops", "tours@swattours.pk", "+92-314-5678901"),
    ("Hunza Journeys", "HUN", "Hunza Journey Makers", "info@hunzajoy.pk", "+92-315-6789012"),
    ("Naran Kaghan", "NAR", "Naran Kaghan Tours", "contact@narankaghan.pk", "+92-316-7890123"),
    ("Chitral Explorers", "CHI", "Chitral Explorer Group", "admin@chiralexp.pk", "+92-317-8901234"),
    ("Abbottabad Tours", "ABB", "Abbottabad Tour Services", "info@abbottabad.pk", "+92-318-9012345"),
    ("Murree Travels", "MUR", "Murree Travel Agency", "tours@murtravel.pk", "+92-319-0123456"),
    ("Galiyat Adventure", "GAL", "Galiyat Adventure Co", "contact@galiyat.pk", "+92-320-1234567"),
    ("Azad Kashmir", "AZK", "Azad Kashmir Tours", "admin@azadkashmirtours.pk", "+92-321-2345678"),
    ("Mirpur Journeys", "MIR", "Mirpur Journey Ltd", "info@mirpurjy.pk", "+92-322-3456789"),
    ("Northern Heights", "NOR", "Northern Heights Tours", "contact@northernheights.pk", "+92-323-4567890"),
    ("Southern Explorations", "SOU", "Southern Explorer Co", "admin@southexp.pk", "+92-324-5678901"),
    ("Eastern Routes", "EAS", "Eastern Routes Travel", "info@easternroutes.pk", "+92-325-6789012"),
    ("Western Voyages", "WES", "Western Voyages Ltd", "tours@westernvoy.pk", "+92-326-7890123"),
    ("Desert Safaris", "DES", "Desert Safari Company", "contact@desertsafari.pk", "+92-327-8901234"),
    ("Mountain Trails", "MTN", "Mountain Trails Tours", "admin@mountaintrails.pk", "+92-328-9012345"),
    ("Heritage Tours", "HER", "Heritage Tours Ltd", "info@heritagetours.pk", "+92-329-0123456"),
    ("Adventure Plus", "ADV", "Adventure Plus Co", "contact@adventureplus.pk", "+92-330-1234567"),
    ("Journey Masters", "JOU", "Journey Masters Inc", "admin@journeymaster.pk", "+92-331-2345678"),
    ("Travel Seekers", "TRA", "Travel Seekers Ltd", "info@travelseekers.pk", "+92-332-3456789"),
    ("Wanderlust Tours", "WAN", "Wanderlust Tour Ops", "tours@wanderlust.pk", "+92-333-4567890"),
    ("Global Journeys", "GLO", "Global Journeys Co", "contact@globaljour.pk", "+92-334-5678901"),
]

class Command(BaseCommand):
    help = 'Add 35 sample vendors to the database'

    def handle(self, *args, **options):
        # Get the first superuser or admin user
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.filter(is_staff=True).first()
        
        if not user:
            self.stdout.write(self.style.ERROR('No admin user found. Please create a superuser first.'))
            return

        created_count = 0
        for name, short_name, company, email, phone in VENDOR_DATA:
            try:
                vendor, created = Vendor.objects.get_or_create(
                    email=email,
                    defaults={
                        'name': name,
                        'short_name': short_name,
                        'company': company,
                        'phone': phone,
                        'created_by': user,
                        'is_active': True,
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Created vendor: {name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'⊘ Vendor already exists: {name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to create {name}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully created {created_count} vendors!'))
