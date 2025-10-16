"""
Complete Customer Sync Management Command
========================================
Syncs customers by:
1. Keeping all production customers (real website data)
2. Adding missing customers from import_customers.py
3. For similar names, uses production version (better contact info)

Total: 17 customers (13 production + 4 missing)
"""

import json
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import RestaurantProfile, PrivateCustomerProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync complete customer list - production data + missing customers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-users',
            action='store_true',
            help='Clear all non-superuser users before syncing',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🏪 COMPLETE CUSTOMER SYNC'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        dry_run = options.get('dry_run', False)
        clear_users = options.get('clear_users', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Clear users if requested
        if clear_users and not dry_run:
            self.clear_all_users()
        
        # Load production customers
        production_customers = self.load_production_customers()
        
        # Get missing customers from import_customers.py
        missing_customers = self.get_missing_customers()
        
        # Show summary
        self.stdout.write(f'\n📊 CUSTOMER SYNC SUMMARY:')
        self.stdout.write(f'   Production customers: {len(production_customers)}')
        self.stdout.write(f'   Missing customers: {len(missing_customers)}')
        self.stdout.write(f'   Total: {len(production_customers) + len(missing_customers)} customers')
        
        # Sync customers
        self.sync_customers(production_customers + missing_customers, dry_run)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🎉 CUSTOMER SYNC COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def clear_all_users(self):
        """Clear all non-superuser users and their profiles"""
        self.stdout.write(self.style.WARNING('🗑️  CLEARING ALL NON-SUPERUSER USERS...'))
        
        try:
            # Clear profiles first (foreign key dependencies)
            restaurant_count = RestaurantProfile.objects.count()
            private_count = PrivateCustomerProfile.objects.count()
            
            RestaurantProfile.objects.all().delete()
            PrivateCustomerProfile.objects.all().delete()
            
            self.stdout.write(f'    🗑️  Cleared {restaurant_count} restaurant profiles')
            self.stdout.write(f'    🗑️  Cleared {private_count} private customer profiles')
            
            # Clear non-superuser users
            user_count = User.objects.filter(is_superuser=False).count()
            if user_count > 0:
                User.objects.filter(is_superuser=False).delete()
                self.stdout.write(f'    🗑️  Cleared {user_count} users (kept superusers)')
            else:
                self.stdout.write(f'    ✅ No non-superuser users to clear')
                
        except Exception as e:
            self.stdout.write(f'    ❌ Error clearing users: {str(e)[:50]}...')

    def load_production_customers(self):
        """Load customers from production_seeding.json"""
        self.stdout.write('📄 Loading production customers...')
        
        seeding_file = os.path.join('data', 'production_seeding.json')
        if not os.path.exists(seeding_file):
            self.stdout.write(self.style.ERROR(f'❌ Production seeding file not found: {seeding_file}'))
            return []
        
        with open(seeding_file, 'r') as f:
            data = json.load(f)
        
        # Flatten the nested customer structure
        all_customers = []
        customers_data = data.get('customers', {})
        for area, customers_list in customers_data.items():
            if isinstance(customers_list, list):
                all_customers.extend(customers_list)
        
        # Filter out private customers (they don't have business_name, only customer_name)
        business_customers = []
        for customer in all_customers:
            if 'business_name' in customer:
                business_customers.append(customer)
        
        self.stdout.write(f'    ✅ Loaded {len(business_customers)} production business customers')
        for customer in business_customers:
            self.stdout.write(f'       - {customer["business_name"]} ({customer.get("email", "no email")})')
        
        if len(all_customers) > len(business_customers):
            private_count = len(all_customers) - len(business_customers)
            self.stdout.write(f'    ℹ️  Skipped {private_count} private customers (not business accounts)')
        
        return business_customers

    def get_missing_customers(self):
        """Get customers that are missing from production"""
        self.stdout.write('🔍 Identifying missing customers...')
        
        # These are the 4 customers missing from production_seeding.json
        missing_customers = [
            {
                'business_name': 'Mugg and Bean',
                'contact_person': 'Restaurant Manager',
                'email': 'orders@muggandbean.co.za',
                'phone': '+27 11 555 0001',
                'address': '123 Coffee Street, Johannesburg, 2000',
                'customer_type': 'restaurant',
                'area': 'Johannesburg',
                'cuisine_type': 'Coffee Shop & Restaurant',
                'is_active': True,
                'delivery_address': 'Mugg and Bean Restaurant, Johannesburg',
                'delivery_instructions': 'Main entrance delivery',
                'order_notes': 'Large order volumes - 30kg potato, 20kg onions, peppers',
                'website': 'https://www.muggandbean.co.za/',
                'payment_terms_days': 30,
                'credit_limit': 25000.00,
            },
            {
                'business_name': 'Debonair Pizza',
                'contact_person': 'Store Manager',
                'email': 'supplies@debonair.co.za',
                'phone': '+27 11 555 0005',
                'address': '654 Pizza Plaza, Midrand, 1685',
                'customer_type': 'restaurant',
                'area': 'Midrand',
                'cuisine_type': 'Pizza Restaurant',
                'is_active': True,
                'delivery_address': 'Debonair Pizza, Midrand',
                'delivery_instructions': 'Delivery to kitchen entrance',
                'order_notes': 'Pizza toppings - tomatoes, mushrooms, onions',
                'website': 'https://www.debonairs.co.za/',
                'payment_terms_days': 21,
                'credit_limit': 15000.00,
            },
            {
                'business_name': 'Venue',
                'contact_person': 'Event Manager',
                'email': 'events@venue.co.za',
                'phone': '+27 11 555 0014',
                'address': '159 Event Plaza, Rosebank, 2196',
                'customer_type': 'restaurant',
                'area': 'Rosebank',
                'cuisine_type': 'Event Venue & Catering',
                'is_active': True,
                'delivery_address': 'Venue Event Center, Rosebank',
                'delivery_instructions': 'Catering entrance - event supplies',
                'order_notes': 'Event catering - tomatoes, mushrooms, onions',
                'website': 'https://venue.co.za/',
                'payment_terms_days': 30,
                'credit_limit': 20000.00,
            },
            {
                'business_name': 'Culinary Institute',
                'contact_person': 'Procurement Officer',
                'email': 'procurement@culinary.edu.za',
                'phone': '+27 11 555 0007',
                'address': '147 Education Drive, Braamfontein, 2017',
                'customer_type': 'institution',
                'area': 'Braamfontein',
                'cuisine_type': 'Culinary Training Institution',
                'is_active': True,
                'delivery_address': 'Culinary Institute, Braamfontein Campus',
                'delivery_instructions': 'Main campus - kitchen training facility',
                'order_notes': 'Educational institution - diverse vegetable requirements',
                'website': 'https://culinary.edu.za/',
                'payment_terms_days': 45,
                'credit_limit': 35000.00,
            },
            {
                'business_name': 'The Rusty Feather',
                'contact_person': 'Restaurant Manager',
                'email': 'hello@rustyfeather.co.za',
                'phone': '079 980 7743',
                'address': 'T-Junction R512 and R104, Hartbeespoort, Broederstroom, 0216',
                'customer_type': 'restaurant',
                'area': 'Hartbeespoort',
                'cuisine_type': 'Restaurant & Cocktail Bar',
                'is_active': True,
                'delivery_address': 'The Rusty Feather, T-Junction Hartbeespoort',
                'delivery_instructions': 'Restaurant entrance - T-Junction location',
                'order_notes': 'Restaurant & bar - weekend brunch specialist, cocktail garnishes needed',
                'website': 'https://rustyfeather.co.za/',
                'payment_terms_days': 21,
                'credit_limit': 18000.00,
                'whatsapp_number': '+27 76 655 4873',  # Different WhatsApp ordering number
            },
        ]
        
        self.stdout.write(f'    ✅ Found {len(missing_customers)} missing customers:')
        for customer in missing_customers:
            self.stdout.write(f'       - {customer["business_name"]} ({customer["email"]})')
        
        return missing_customers

    def sync_customers(self, customers_data, dry_run):
        """Sync all customers"""
        self.stdout.write('🏪 Syncing customers...')
        
        if dry_run:
            self.stdout.write(f'    Would create {len(customers_data)} customers:')
            for customer in customers_data:
                self.stdout.write(f'    - {customer["business_name"]} ({customer.get("customer_type", "restaurant")})')
            return
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for customer_data in customers_data:
                try:
                    # Create user first
                    user, user_created = User.objects.get_or_create(
                        email=customer_data['email'],
                        defaults={
                            'first_name': customer_data.get('contact_person', '').split()[0] if customer_data.get('contact_person') else 'Manager',
                            'last_name': customer_data.get('contact_person', '').split()[-1] if customer_data.get('contact_person') and len(customer_data.get('contact_person', '').split()) > 1 else '',
                            'user_type': 'restaurant',
                            'phone': customer_data.get('phone', ''),
                            'is_active': customer_data.get('is_active', True),
                            'is_staff': False,
                            'is_superuser': False,
                        }
                    )
                    
                    if user_created:
                        user.set_password('defaultpassword123')
                        user.save()
                    
                    # Create appropriate profile
                    if customer_data.get('customer_type') == 'private':
                        profile, profile_created = PrivateCustomerProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                'customer_type': 'household',
                                'delivery_address': customer_data.get('delivery_address', customer_data.get('address', '')),
                                'delivery_instructions': customer_data.get('delivery_instructions', ''),
                                'preferred_delivery_day': 'tuesday',
                                'whatsapp_number': customer_data.get('phone', ''),
                                'credit_limit': Decimal(str(customer_data.get('credit_limit', 5000.00))),
                                'order_notes': customer_data.get('order_notes', ''),
                            }
                        )
                    else:
                        # Business customer - parse address
                        address_parts = customer_data.get('address', '').split(',')
                        address = address_parts[0].strip() if address_parts else customer_data.get('address', 'Address')
                        city = address_parts[1].strip() if len(address_parts) > 1 else customer_data.get('area', 'Hartbeespoort')
                        postal_code = address_parts[2].strip() if len(address_parts) > 2 else '0216'
                        
                        profile, profile_created = RestaurantProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                'business_name': customer_data['business_name'],
                                'branch_name': customer_data.get('branch_name', ''),
                                'business_registration': customer_data.get('business_registration', ''),
                                'address': address,
                                'city': city,
                                'postal_code': postal_code,
                                'payment_terms': f"{customer_data.get('payment_terms_days', 30)} days",
                                'is_private_customer': customer_data.get('customer_type') == 'private',
                                'delivery_notes': customer_data.get('delivery_instructions', ''),
                                'order_pattern': customer_data.get('order_notes', ''),
                            }
                        )
                    
                    if user_created or profile_created:
                        created_count += 1
                        self.stdout.write(f'    ✅ Created: {customer_data["business_name"]}')
                    else:
                        # Update existing
                        user.phone = customer_data.get('phone', user.phone)
                        user.save()
                        
                        if hasattr(profile, 'business_name'):  # Restaurant profile
                            profile.business_name = customer_data['business_name']
                            profile.delivery_notes = customer_data.get('delivery_instructions', profile.delivery_notes)
                            profile.order_pattern = customer_data.get('order_notes', profile.order_pattern)
                            profile.save()
                        
                        updated_count += 1
                        self.stdout.write(f'    🔄 Updated: {customer_data["business_name"]}')
                        
                except Exception as e:
                    error_count += 1
                    business_name = customer_data.get('business_name', 'Unknown')
                    self.stdout.write(f'    ❌ Error creating {business_name}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 SYNC RESULTS:'))
        self.stdout.write(f'   ✅ Created: {created_count} customers')
        self.stdout.write(f'   🔄 Updated: {updated_count} customers')
        self.stdout.write(f'   ❌ Errors: {error_count} customers')
        self.stdout.write(f'   📱 Total: {created_count + updated_count} customers synced')
        
        if error_count == 0:
            self.stdout.write(self.style.SUCCESS('🎉 All customers synced successfully!'))
