from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.tickets.models import Ticket
from apps.vendors.models import Vendor
from datetime import timedelta
import random
from decimal import Decimal

User = get_user_model()

CUSTOMERS = [
    'Ahmed Hassan', 'Fatima Khan', 'Ali Sheikh', 'Zainab Ibrahim',
    'Hassan Ali', 'Aisha Mohammed', 'Omar Abdullah', 'Leena Ahmed',
    'Karim Sultan', 'Noor Hassan', 'Bilal Khan', 'Hana Ibrahim',
    'Salim Ahmed', 'Dina Mohammad', 'Ibrahim Hassan', 'Sara Khan',
    'Mohammed Ali', 'Amira Hassan', 'Rashid Khan', 'Layla Ahmed',
]


class Command(BaseCommand):
    help = 'Create 40 test ticket records (25 PKR + 15 SAR, 25 Credit + 15 Debit)'

    def handle(self, *args, **options):
        # Get first user (admin)
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('No users found. Create a user first.'))
            return

        # Get vendors
        vendors = list(Vendor.objects.all())
        if not vendors:
            self.stdout.write(self.style.ERROR('No vendors found. Create vendors first.'))
            return

        # Create 40 tickets
        tickets = []
        base_date = timezone.now().date()

        for i in range(40):
            # Distribution: 25 PKR + 15 SAR
            is_sar = i >= 25
            currency = 'SAR' if is_sar else 'PKR'

            # Distribution: 25 Credit + 15 Debit
            is_debit = i >= 25
            payment_type = 'Debit' if is_debit else 'Credit'

            invoice_no = f'INV-2024-{str(i + 1).zfill(4)}'
            customer = random.choice(CUSTOMERS)
            vendor = random.choice(vendors)

            # Random ticket quantities
            adt_qty = random.randint(1, 3)
            chd_qty = random.randint(0, 2)
            inf_qty = random.randint(0, 1)

            # Random rates based on currency
            if is_sar:
                adt_rate = Decimal(str(random.randint(800, 1200)))
                chd_rate = Decimal(str(random.randint(400, 700)))
                inf_rate = Decimal(str(random.randint(100, 300)))
                exchange_rate = Decimal(str(round(random.uniform(0.10, 0.15), 4)))
            else:
                adt_rate = Decimal(str(random.randint(40000, 60000)))
                chd_rate = Decimal(str(random.randint(20000, 35000)))
                inf_rate = Decimal(str(random.randint(5000, 15000)))
                exchange_rate = Decimal('1.0000')

            # Calculate total amount
            total_amount = (
                (adt_qty * adt_rate) +
                (chd_qty * chd_rate) +
                (inf_qty * inf_rate)
            )

            # PKR amount
            if is_sar:
                pkr_amount = total_amount * exchange_rate
            else:
                pkr_amount = total_amount

            issued_date = base_date - timedelta(days=random.randint(0, 60))
            dep_date = issued_date + timedelta(days=random.randint(1, 30))

            ticket = Ticket(
                vendor=vendor,
                created_by=user,
                customer_name=customer,
                invoice_no=invoice_no,
                issued_date=issued_date,
                departure_date=dep_date,
                adt_qty=adt_qty,
                adt_rate=adt_rate,
                chd_qty=chd_qty,
                chd_rate=chd_rate,
                inf_qty=inf_qty,
                inf_rate=inf_rate,
                total_amount=total_amount,
                payment_type=payment_type,
                currency=currency,
                exchange_rate=exchange_rate,
                pkr_amount=pkr_amount,
                description=f'Airline ticket for {customer}'
            )
            tickets.append(ticket)

        # Bulk create
        created = Ticket.objects.bulk_create(tickets)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Successfully created {len(created)} test tickets:\n'
                              f'  ✓ 25 PKR + 15 SAR\n'
                              f'  ✓ 25 Credit + 15 Debit')
        )
