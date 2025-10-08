"""
Custom seeding command for production_seeding.json file
Seeds the database with the production data including real customer details
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import RestaurantProfile, FarmProfile, PrivateCustomerProfile
from products.models import Product, Department
from suppliers.models import Supplier
from settings.models import UnitOfMeasure
from decimal import Decimal
import json
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed database from production_seeding.json file with real customer and supplier data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before seeding (DANGEROUS)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be seeded without making changes',
        )

    def handle(self, *args, **options):
        clear_existing = options['clear_existing']
        dry_run = options['dry_run']
        
        production_file = 'data/production_seeding.json'
        
        if not os.path.exists(production_file):
            self.stdout.write(self.style.ERROR(f'Production seeding file not found: {production_file}'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('=== PRODUCTION SEEDING FROM production_seeding.json ==='))
        
        if clear_existing and not dry_run:
            self.clear_existing_data()
        
        # Load production data
        with open(production_file, 'r') as f:
            data = json.load(f)
        
        # Seed in dependency order
        self.seed_suppliers(data, dry_run)
        self.seed_users(data, dry_run)
        self.seed_customers(data, dry_run)
        self.seed_units_of_measure(data, dry_run)
        
        # Note about products
        self.stdout.write(self.style.WARNING('📦 Products: Using reference to updated_seeding/products_and_departments.json'))
        self.stdout.write(self.style.WARNING('    Run: python manage.py seed_updated_products --seeding-dir updated_seeding'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETED - No actual changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('🎉 PRODUCTION SEEDING FROM JSON COMPLETED!'))
            self.stdout.write(self.style.WARNING('⚠️  Remember to seed products separately with updated_seeding data'))

    def clear_existing_data(self):
        """Clear existing data (use with extreme caution)"""
        self.stdout.write(self.style.WARNING('⚠️  CLEARING EXISTING DATA...'))
        
        with transaction.atomic():
            # Clear profiles first
            RestaurantProfile.objects.all().delete()
            FarmProfile.objects.all().delete()
            PrivateCustomerProfile.objects.all().delete()
            
            # Clear users (except superusers)
            User.objects.filter(is_superuser=False).delete()
            
            # Clear suppliers
            Supplier.objects.all().delete()
            
        self.stdout.write(self.style.SUCCESS('✅ Existing data cleared'))

    def seed_suppliers(self, data, dry_run):
        """Seed suppliers from production data"""
        self.stdout.write('🏭 Seeding Suppliers...')
        
        suppliers_data = data.get('suppliers', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(suppliers_data)} suppliers')
            for supplier in suppliers_data:
                self.stdout.write(f'    - {supplier["name"]}')
            return
        
        created_count = 0
        with transaction.atomic():
            for supplier_data in suppliers_data:
                supplier, created = Supplier.objects.get_or_create(
                    name=supplier_data['name'],
                    defaults={
                        'contact_person': supplier_data.get('contact_person', ''),
                        'phone': supplier_data.get('phone', ''),
                        'email': supplier_data.get('email', ''),
                        'address': supplier_data.get('address', ''),
                        'supplier_type': supplier_data.get('supplier_type', 'external'),
                        'registration_number': supplier_data.get('registration_number', ''),
                        'tax_number': supplier_data.get('tax_number', ''),
                        'payment_terms_days': supplier_data.get('payment_terms_days', 30),
                        'lead_time_days': supplier_data.get('lead_time_days', 7),
                        'minimum_order_value': supplier_data.get('minimum_order_value'),
                        'is_active': supplier_data.get('is_active', True),
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} suppliers'))

    def seed_users(self, data, dry_run):
        """Seed users from production data"""
        self.stdout.write('👥 Seeding Users...')
        
        users_data = data.get('users', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(users_data)} users')
            for user in users_data:
                self.stdout.write(f'    - {user["email"]} ({user.get("user_type", "unknown")})')
            return
        
        created_count = 0
        with transaction.atomic():
            for user_data in users_data:
                user, created = User.objects.get_or_create(
                    email=user_data['email'],
                    defaults={
                        'first_name': user_data.get('first_name', ''),
                        'last_name': user_data.get('last_name', ''),
                        'phone': user_data.get('phone', ''),
                        'is_verified': user_data.get('is_verified', False),
                        'is_active': user_data.get('is_active', True),
                        'is_staff': user_data.get('is_staff', False),
                        'is_superuser': user_data.get('is_superuser', False),
                    }
                )
                if created:
                    created_count += 1
                    
                    # Create appropriate profile based on user_type
                    user_type = user_data.get('user_type', 'private')
                    if user_type in ['admin', 'farm_manager', 'stock_taker']:
                        # Map user types to positions and access levels
                        position_map = {
                            'admin': ('System Administrator', 'admin'),
                            'farm_manager': ('Farm Manager', 'manager'),
                            'stock_taker': ('Stock Controller', 'basic'),
                        }
                        position, access_level = position_map.get(user_type, ('Staff', 'basic'))
                        
                        # Set permissions based on user type
                        permissions = {
                            'admin': {
                                'can_manage_inventory': True,
                                'can_approve_orders': True,
                                'can_manage_customers': True,
                                'can_view_reports': True,
                            },
                            'farm_manager': {
                                'can_manage_inventory': True,
                                'can_approve_orders': True,
                                'can_manage_customers': True,
                                'can_view_reports': True,
                            },
                            'stock_taker': {
                                'can_manage_inventory': True,
                                'can_approve_orders': False,
                                'can_manage_customers': False,
                                'can_view_reports': True,
                            },
                        }
                        
                        FarmProfile.objects.get_or_create(
                            user=user,
                            defaults={
                                'employee_id': f'{user_type.upper()}-001',
                                'department': 'Operations',
                                'position': position,
                                'whatsapp_number': user_data.get('phone', ''),
                                'access_level': access_level,
                                'notes': f'Production seeded {user_type} profile',
                                **permissions.get(user_type, {})
                            }
                        )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} users'))

    def seed_customers(self, data, dry_run):
        """Seed customer profiles from production data"""
        self.stdout.write('🍽️ Seeding Customers...')
        
        customers_data = data.get('customers', {})
        
        total_customers = 0
        for area, customers in customers_data.items():
            if area == 'private_customers':
                total_customers += len(customers)
            else:
                total_customers += len(customers)
        
        if dry_run:
            self.stdout.write(f'    Would create {total_customers} customers')
            for area, customers in customers_data.items():
                self.stdout.write(f'    {area}: {len(customers)} customers')
                for customer in customers:
                    name = customer.get('business_name', customer.get('customer_name', 'Unknown'))
                    self.stdout.write(f'      - {name}')
            return
        
        created_count = 0
        with transaction.atomic():
            # Restaurant customers
            for area, customers in customers_data.items():
                if area == 'private_customers':
                    continue
                    
                for customer_data in customers:
                    # Create user for restaurant
                    user, user_created = User.objects.get_or_create(
                        email=customer_data['email'],
                        defaults={
                            'first_name': customer_data['business_name'],
                            'last_name': 'Restaurant',
                            'phone': customer_data.get('phone', ''),
                            'is_active': True,
                        }
                    )
                    
                    # Create restaurant profile
                    # Extract city and postal code from address
                    address = customer_data.get('address', '')
                    city = 'Sun City' if 'Sun City' in address else 'Mooi Nooi' if 'Mooi Nooi' in address else 'Unknown'
                    postal_code = '0316' if 'Sun City' in address else '0216' if 'Mooi Nooi' in address else '0000'
                    
                    profile, profile_created = RestaurantProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'business_name': customer_data['business_name'],
                            'branch_name': customer_data.get('branch_type', ''),
                            'business_registration': customer_data.get('business_registration', ''),
                            'address': address,
                            'city': city,
                            'postal_code': postal_code,
                            'payment_terms': 'Net 30',
                            'is_private_customer': False,
                            'delivery_notes': customer_data.get('delivery_instructions', ''),
                            'order_pattern': customer_data.get('order_notes', ''),
                        }
                    )
                    
                    if profile_created:
                        created_count += 1
            
            # Private customers
            private_customers = customers_data.get('private_customers', [])
            for customer_data in private_customers:
                # Create user for private customer
                user, user_created = User.objects.get_or_create(
                    email=customer_data['email'],
                    defaults={
                        'first_name': customer_data.get('customer_name', '').split()[0] if customer_data.get('customer_name') else 'Private',
                        'last_name': 'Customer',
                        'phone': customer_data.get('phone', ''),
                        'is_active': True,
                    }
                )
                
                # Create private customer profile
                profile, profile_created = PrivateCustomerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'customer_type': 'household',
                        'delivery_address': customer_data.get('delivery_address', 'Private Address - Confidential'),
                        'delivery_instructions': customer_data.get('delivery_instructions', ''),
                        'preferred_delivery_day': 'tuesday',
                        'whatsapp_number': customer_data.get('phone', ''),
                        'credit_limit': Decimal('1000.00'),
                        'order_notes': customer_data.get('order_notes', ''),
                    }
                )
                
                if profile_created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} customer profiles'))

    def seed_units_of_measure(self, data, dry_run):
        """Seed units of measure from production data"""
        self.stdout.write('📏 Seeding Units of Measure...')
        
        units_data = data.get('units_of_measure', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(units_data)} units')
            for unit in units_data:
                self.stdout.write(f'    - {unit["name"]} ({unit.get("category", "unknown")})')
            return
        
        created_count = 0
        with transaction.atomic():
            for unit_data in units_data:
                unit, created = UnitOfMeasure.objects.get_or_create(
                    name=unit_data['name'],
                    defaults={
                        'category': unit_data.get('category', 'unit'),
                        'description': unit_data.get('description', ''),
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} units of measure'))

    def seed_products(self, data, dry_run):
        """Seed products from production data"""
        self.stdout.write('📦 Seeding Products...')
        
        products_data = data.get('products', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(products_data)} products')
            for i, product in enumerate(products_data[:5]):
                self.stdout.write(f'    - {product["name"]} ({product.get("unit", "kg")}) - {product.get("department", "Unknown")}')
            if len(products_data) > 5:
                self.stdout.write(f'    ... and {len(products_data) - 5} more')
            return
        
        from products.models import Product, Department
        from decimal import Decimal
        
        created_count = 0
        with transaction.atomic():
            for product_data in products_data:
                # Get or create department
                dept_name = product_data.get('department', 'Vegetables')
                department, _ = Department.objects.get_or_create(
                    name=dept_name,
                    defaults={'description': f'{dept_name} department'}
                )
                
                try:
                    product, created = Product.objects.get_or_create(
                        name=product_data['name'],
                        unit=product_data.get('unit', 'kg'),
                        defaults={
                            'description': product_data.get('description', ''),
                            'department': department,
                            'price': Decimal(str(product_data.get('price', 0))),
                            'stock_level': product_data.get('stock_level', 0),
                            'minimum_stock': product_data.get('minimum_stock', 5),
                            'is_active': product_data.get('is_active', True),
                        }
                    )
                    if created:
                        created_count += 1
                        
                except Exception as e:
                    self.stdout.write(f'    ❌ Error creating {product_data["name"]}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} products'))
