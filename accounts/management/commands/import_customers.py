from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User, RestaurantProfile
from products.models import Department
import random


class Command(BaseCommand):
    help = 'Import customer names from WhatsApp messages with dummy data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing customers before importing',
        )

    def handle(self, *args, **options):
        # Customer names extracted from WhatsApp messages
        customers_data = [
            {
                'name': 'Mugg and Bean',
                'type': 'restaurant',
                'contact_person': 'Restaurant Manager',
                'phone': '+27 11 555 0001',
                'email': 'orders@muggandbean.co.za',
                'address': '123 Coffee Street, Johannesburg, 2000',
                'credit_limit': 15000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'Luma Restaurant',
                'type': 'restaurant',
                'contact_person': 'Head Chef',
                'phone': '+27 11 555 0002',
                'email': 'kitchen@luma.co.za',
                'address': '456 Fine Dining Ave, Sandton, 2196',
                'credit_limit': 25000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'Maltos',
                'type': 'restaurant',
                'contact_person': 'Operations Manager',
                'phone': '+27 11 555 0003',
                'email': 'procurement@maltos.co.za',
                'address': '789 Restaurant Row, Rosebank, 2196',
                'credit_limit': 20000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'Shebeen',
                'type': 'restaurant',
                'contact_person': 'Owner',
                'phone': '+27 11 555 0004',
                'email': 'orders@shebeen.co.za',
                'address': '321 Traditional Way, Soweto, 1809',
                'credit_limit': 10000.00,
                'payment_terms_days': 14,
            },
            {
                'name': 'Debonair Pizza',
                'type': 'restaurant',
                'contact_person': 'Store Manager',
                'phone': '+27 11 555 0005',
                'email': 'supplies@debonair.co.za',
                'address': '654 Pizza Plaza, Midrand, 1685',
                'credit_limit': 12000.00,
                'payment_terms_days': 21,
            },
            {
                'name': 'Casa Bella',
                'type': 'restaurant',
                'contact_person': 'Executive Chef',
                'phone': '+27 11 555 0006',
                'email': 'chef@casabella.co.za',
                'address': '987 Italian Street, Melville, 2109',
                'credit_limit': 18000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'Culinary Institute',
                'type': 'institution',
                'contact_person': 'Procurement Officer',
                'phone': '+27 11 555 0007',
                'email': 'procurement@culinary.edu.za',
                'address': '147 Education Drive, Braamfontein, 2017',
                'credit_limit': 30000.00,
                'payment_terms_days': 45,
            },
            {
                'name': 'Order Valley',
                'type': 'restaurant',
                'contact_person': 'General Manager',
                'phone': '+27 11 555 0008',
                'email': 'gm@ordervalley.co.za',
                'address': '258 Valley Road, Fourways, 2055',
                'credit_limit': 22000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'Barchef Entertainment',
                'type': 'entertainment',
                'contact_person': 'Bar Manager',
                'phone': '+27 11 555 0009',
                'email': 'bar@barchef.co.za',
                'address': '369 Entertainment District, Newtown, 2001',
                'credit_limit': 16000.00,
                'payment_terms_days': 21,
            },
            {
                'name': 'Pecanwood Golf Estate',
                'type': 'hospitality',
                'contact_person': 'Food & Beverage Manager',
                'phone': '+27 12 555 0010',
                'email': 'fb@pecanwood.co.za',
                'address': '741 Golf Course Road, Hartbeespoort, 0216',
                'credit_limit': 35000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'Wimpy',
                'type': 'restaurant',
                'contact_person': 'Store Manager',
                'phone': '+27 11 555 0011',
                'email': 'orders@wimpy.co.za',
                'address': '852 Mooikloof Drive, Pretoria, 0081',
                'credit_limit': 14000.00,
                'payment_terms_days': 21,
            },
            {
                'name': 'Marco',
                'type': 'restaurant',
                'contact_person': 'Kitchen Manager',
                'phone': '+27 11 555 0012',
                'email': 'kitchen@marco.co.za',
                'address': '963 Restaurant Street, Johannesburg, 2001',
                'credit_limit': 16000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'T-junction',
                'type': 'restaurant',
                'contact_person': 'Operations Manager',
                'phone': '+27 11 555 0013',
                'email': 'ops@tjunction.co.za',
                'address': '741 Junction Road, Sandton, 2196',
                'credit_limit': 13000.00,
                'payment_terms_days': 21,
            },
            {
                'name': 'Venue',
                'type': 'restaurant',
                'contact_person': 'Event Manager',
                'phone': '+27 11 555 0014',
                'email': 'events@venue.co.za',
                'address': '159 Event Plaza, Rosebank, 2196',
                'credit_limit': 20000.00,
                'payment_terms_days': 30,
            },
            {
                'name': 'SHALLOME',
                'type': 'restaurant',
                'contact_person': 'Restaurant Manager',
                'phone': '+27 11 555 0015',
                'email': 'manager@shallome.co.za',
                'address': '357 Heritage Street, Johannesburg, 2001',
                'credit_limit': 12000.00,
                'payment_terms_days': 21,
            },
            {
                'name': 'Hazvinei',
                'type': 'restaurant',
                'contact_person': 'Owner',
                'phone': '+27 11 555 0016',
                'email': 'owner@hazvinei.co.za',
                'address': '486 Cultural Avenue, Soweto, 1809',
                'credit_limit': 11000.00,
                'payment_terms_days': 14,
            },
        ]

        if options['clear']:
            self.stdout.write('Clearing existing restaurant profiles and users...')
            RestaurantProfile.objects.all().delete()
            User.objects.filter(user_type='restaurant').delete()
            self.stdout.write(self.style.SUCCESS('Existing restaurant data cleared.'))

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for customer_data in customers_data:
                # Create or get user
                user, user_created = User.objects.get_or_create(
                    email=customer_data['email'],
                    defaults={
                        'first_name': customer_data['contact_person'].split()[0] if customer_data['contact_person'] else 'Manager',
                        'last_name': customer_data['contact_person'].split()[-1] if len(customer_data['contact_person'].split()) > 1 else '',
                        'phone': customer_data['phone'],
                        'user_type': 'restaurant',
                        'is_active': True,
                    }
                )

                # Create or get restaurant profile
                profile, profile_created = RestaurantProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'business_name': customer_data['name'],
                        'address': customer_data['address'],
                        'city': 'Johannesburg',  # Default city
                        'postal_code': '2000',   # Default postal code
                        'payment_terms': f"{customer_data['payment_terms_days']} days",
                    }
                )

                if user_created or profile_created:
                    created_count += 1
                    self.stdout.write(f'Created restaurant: {customer_data["name"]} ({customer_data["email"]})')
                else:
                    # Update existing data
                    user.phone = customer_data['phone']
                    user.save()
                    
                    profile.business_name = customer_data['name']
                    profile.address = customer_data['address']
                    profile.payment_terms = f"{customer_data['payment_terms_days']} days"
                    profile.save()
                    
                    updated_count += 1
                    self.stdout.write(f'Updated restaurant: {customer_data["name"]}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported restaurants: {created_count} created, {updated_count} updated'
            )
        )
