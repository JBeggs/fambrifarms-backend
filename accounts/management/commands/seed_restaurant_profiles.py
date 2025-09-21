from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from accounts.models import User, RestaurantProfile
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed restaurant profiles based on WhatsApp company extraction system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing restaurant profiles before importing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing restaurant profiles...')
            RestaurantProfile.objects.all().delete()
            User.objects.filter(user_type='restaurant').delete()
            self.stdout.write(self.style.SUCCESS('Existing restaurant data cleared.'))

        self.create_restaurant_profiles()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 RESTAURANT PROFILES SEEDED SUCCESSFULLY!'
            )
        )
        self.stdout.write(f'🏪 Restaurant customers from WhatsApp company extraction')
        self.stdout.write(f'📱 Based on actual companies found in WhatsApp messages')
        self.stdout.write(f'✅ Customer dropdown will now show real companies')

    def create_restaurant_profiles(self):
        """Create restaurant profiles based on WhatsApp company extractor"""
        
        # Get companies from WhatsApp system
        from whatsapp.processors.company_extractor import get_company_extractor
        
        company_extractor = get_company_extractor()
        company_aliases = company_extractor.company_aliases
        
        # Get canonical company names (remove duplicates)
        canonical_companies = set(company_aliases.values())
        
        # Restaurant data based on real WhatsApp companies
        restaurant_data = {
            "Mugg and Bean": {
                'branch_name': 'Centurion',
                'address': '123 Coffee Street, Centurion, 0157',
                'city': 'Centurion',
                'phone': '+27 12 345 6789',
                'email': 'orders@muggandbean.co.za',
                'payment_terms': 'Net 30',
                'notes': 'Coffee shop chain - regular orders for fresh produce'
            },
            "Maltos": {
                'branch_name': '',
                'address': '456 Restaurant Avenue, Johannesburg, 2001',
                'city': 'Johannesburg', 
                'phone': '+27 11 234 5678',
                'email': 'orders@maltos.co.za',
                'payment_terms': 'Net 14',
                'notes': 'Restaurant - regular vegetable orders'
            },
            "Valley": {
                'branch_name': '',
                'address': '789 Valley Road, Pretoria, 0001',
                'city': 'Pretoria',
                'phone': '+27 12 987 6543',
                'email': 'orders@valley.co.za',
                'payment_terms': 'Net 30',
                'notes': 'Restaurant - mixed produce orders'
            },
            "Barchef Entertainment": {
                'branch_name': '',
                'address': '321 Entertainment District, Johannesburg, 2001',
                'city': 'Johannesburg',
                'phone': '+27 11 876 5432',
                'email': 'orders@barchef.co.za',
                'payment_terms': 'Net 21',
                'notes': 'Entertainment venue - herbs and specialty items'
            },
            "Casa Bella": {
                'branch_name': '',
                'address': '654 Italian Quarter, Johannesburg, 2001',
                'city': 'Johannesburg',
                'phone': '+27 11 765 4321',
                'email': 'orders@casabella.co.za',
                'payment_terms': 'Net 14',
                'notes': 'Italian restaurant - fresh herbs and vegetables'
            },
            "Debonairs Pizza": {
                'branch_name': 'Centurion',
                'address': '987 Pizza Plaza, Centurion, 0157',
                'city': 'Centurion',
                'phone': '+27 12 654 3210',
                'email': 'orders@debonairs.co.za',
                'payment_terms': 'Net 7',
                'notes': 'Pizza chain - regular vegetable orders'
            },
            "Wimpy Mooikloof": {
                'branch_name': 'Mooikloof',
                'address': '147 Mooikloof Ridge, Pretoria, 0081',
                'city': 'Pretoria',
                'phone': '+27 12 543 2109',
                'email': 'mooikloof@wimpy.co.za',
                'payment_terms': 'Net 14',
                'notes': 'Family restaurant - lettuce, tomatoes, onions'
            },
            "T-junction": {
                'branch_name': '',
                'address': '258 Junction Street, Johannesburg, 2001',
                'city': 'Johannesburg',
                'phone': '+27 11 432 1098',
                'email': 'orders@tjunction.co.za',
                'payment_terms': 'Net 21',
                'notes': 'Restaurant - mixed vegetable orders'
            },
            "Culinary Institute": {
                'branch_name': '',
                'address': '369 Education Drive, Pretoria, 0002',
                'city': 'Pretoria',
                'phone': '+27 12 321 0987',
                'email': 'orders@culinary.edu.za',
                'payment_terms': 'Net 30',
                'notes': 'Culinary school - herbs in punnets, educational orders'
            },
            "Pecanwood Golf Estate": {
                'branch_name': 'Clubhouse',
                'address': 'Pecanwood Golf Estate, Hartbeespoort, 0216',
                'city': 'Hartbeespoort',
                'phone': '+27 12 210 9876',
                'email': 'catering@pecanwood.co.za',
                'payment_terms': 'Net 30',
                'notes': 'Golf estate restaurant - upmarket produce'
            },
            "Venue": {
                'branch_name': '',
                'address': '741 Event Avenue, Johannesburg, 2001',
                'city': 'Johannesburg',
                'phone': '+27 11 109 8765',
                'email': 'orders@venue.co.za',
                'payment_terms': 'Net 14',
                'notes': 'Event venue - variable orders for functions'
            },
            "Revue Bar": {
                'branch_name': '',
                'address': '852 Nightlife Street, Johannesburg, 2001',
                'city': 'Johannesburg',
                'phone': '+27 11 098 7654',
                'email': 'orders@revuebar.co.za',
                'payment_terms': 'Net 7',
                'notes': 'Bar and grill - fresh produce for kitchen'
            },
            "Luma": {
                'branch_name': '',
                'address': '963 Business District, Johannesburg, 2001',
                'city': 'Johannesburg',
                'phone': '+27 11 555 0123',
                'email': 'orders@luma.co.za',
                'payment_terms': 'Net 14',
                'notes': 'Restaurant - regular orders for mint, strawberries, vegetables'
            },
            "Leopard Lodge": {
                'branch_name': '',
                'address': 'Leopard Lodge, Hartbeespoort, 0216',
                'city': 'Hartbeespoort',
                'phone': '+27 12 555 0456',
                'email': 'orders@leopardlodge.co.za',
                'payment_terms': 'Net 30',
                'notes': 'Lodge restaurant - upmarket dining establishment'
            },
            # # Internal/System companies
            # "SHALLOME": {
            #     'branch_name': 'Stock Control',
            #     'address': 'Fambri Farms, Hartbeespoort, North West, 0216',
            #     'city': 'Hartbeespoort',
            #     'phone': '+27 61 674 9368',
            #     'email': 'hazvinei@fambrifarms.co.za',
            #     'payment_terms': 'Immediate',
            #     'notes': 'Internal stock controller - Hazvinei sends daily stock reports'
            # }
        }

        created_count = 0
        
        for company_name in canonical_companies:
            # Skip some extracted companies that aren't real restaurants
            skip_companies = [
                'Morning', 'Morning.', 'Order For Tomorrow', 'Good Day Orders For Tomorrow',
                'Veg Order:', '200G Parsley', 'Shebeen', 'Delivery', 'Leopard', 'Revue'
            ]
            
            if company_name in skip_companies:
                continue
                
            # Use predefined data if available, otherwise create generic data
            if company_name in restaurant_data:
                company_info = restaurant_data[company_name]
            else:
                # Generic data for companies not in our predefined list
                company_info = {
                    'branch_name': '',
                    'address': f'{company_name} Restaurant, Johannesburg, 2001',
                    'city': 'Johannesburg',
                    'phone': '+27 11 000 0000',
                    'email': f'orders@{company_name.lower().replace(" ", "").replace("-", "")}.co.za',
                    'payment_terms': 'Net 30',
                    'notes': f'Restaurant customer - {company_name}'
                }
            
            with transaction.atomic():
                # Create user for the restaurant
                email = company_info['email']
                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': company_name.split()[0],
                        'last_name': 'Restaurant' if len(company_name.split()) == 1 else ' '.join(company_name.split()[1:]),
                        'phone': company_info['phone'],
                        'user_type': 'restaurant',
                        'is_active': True,
                    }
                )
                
                if user_created:
                    user.set_password('FambriFarms2025!')  # Default password
                    user.save()
                    self.stdout.write(f'👤 Created restaurant user: {user.email}')
                
                # Create restaurant profile
                profile, profile_created = RestaurantProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'business_name': company_name,
                        'branch_name': company_info['branch_name'],
                        'address': company_info['address'],
                        'city': company_info['city'],
                        'postal_code': '0001',  # Default postal code
                        'payment_terms': company_info['payment_terms'],
                        'business_registration': f'{company_name.replace(" ", "").upper()}2024/001',
                        'delivery_notes': company_info['notes'],
                        'order_pattern': f'Regular orders from {company_name}',
                    }
                )
                
                if profile_created:
                    created_count += 1
                    self.stdout.write(f'🏪 Created restaurant profile: {profile.business_name}')
                    if company_info['branch_name']:
                        self.stdout.write(f'   📍 Branch: {company_info["branch_name"]} - {company_info["city"]}')
                    else:
                        self.stdout.write(f'   📍 Location: {company_info["city"]}')
                    self.stdout.write(f'   💳 Payment terms: {company_info["payment_terms"]}')
                    
                    # Add to restaurant customers group
                    try:
                        group = Group.objects.get(name='Restaurant Customers')
                        user.groups.add(group)
                    except Group.DoesNotExist:
                        # Create the group if it doesn't exist
                        group = Group.objects.create(name='Restaurant Customers')
                        user.groups.add(group)
                        self.stdout.write(f'🔐 Created group: Restaurant Customers')
                else:
                    self.stdout.write(f'🔄 Restaurant profile already exists: {profile.business_name}')

        self.stdout.write(f'🏪 Created {created_count} restaurant profiles')
        self.stdout.write(f'📱 Based on {len(canonical_companies)} companies from WhatsApp extraction')
