"""
CONSOLIDATED Production Database Seeding Command
This is the ONLY command needed to seed a complete production database
Replaces all the scattered seeding commands with one comprehensive solution
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import RestaurantProfile, FarmProfile, PrivateCustomerProfile
from products.models import Product, Department
from suppliers.models import Supplier, SalesRep, SupplierProduct
from inventory.models import PricingRule
from settings.models import UnitOfMeasure
from decimal import Decimal
import json
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'CONSOLIDATED production seeding - seeds EVERYTHING needed for production'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-all',
            action='store_true',
            help='Clear ALL existing data before seeding (DANGEROUS)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be seeded without making changes',
        )

    def handle(self, *args, **options):
        clear_all = options['clear_all']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('=== CONSOLIDATED PRODUCTION SEEDING ==='))
        
        if clear_all and not dry_run:
            self.clear_all_data()
        
        # Seed in dependency order
        self.seed_units_of_measure(dry_run)
        self.seed_departments(dry_run)
        self.seed_products(dry_run)
        self.seed_suppliers(dry_run)
        self.seed_supplier_products(dry_run)
        self.seed_users(dry_run)
        self.seed_customers(dry_run)
        self.seed_pricing_rules(dry_run)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETED - No actual changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('🎉 CONSOLIDATED PRODUCTION SEEDING COMPLETED!'))
            self.print_summary()

    def clear_all_data(self):
        """Clear ALL existing data"""
        self.stdout.write(self.style.WARNING('⚠️  CLEARING ALL EXISTING DATA...'))
        
        with transaction.atomic():
            # Clear in reverse dependency order
            SupplierProduct.objects.all().delete()
            SalesRep.objects.all().delete()
            Supplier.objects.all().delete()
            
            RestaurantProfile.objects.all().delete()
            FarmProfile.objects.all().delete()
            PrivateCustomerProfile.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            
            PricingRule.objects.all().delete()
            Product.objects.all().delete()
            Department.objects.all().delete()
            UnitOfMeasure.objects.all().delete()
            
        self.stdout.write(self.style.SUCCESS('✅ All existing data cleared'))

    def load_production_data(self):
        """Load production seeding data"""
        production_file = 'data/production_seeding.json'
        if not os.path.exists(production_file):
            raise FileNotFoundError(f'Production seeding file not found: {production_file}')
        
        with open(production_file, 'r') as f:
            return json.load(f)

    def load_updated_seeding_data(self, filename):
        """Load data from updated_seeding directory"""
        file_path = os.path.join('updated_seeding', filename)
        if not os.path.exists(file_path):
            self.stdout.write(self.style.WARNING(f'Updated seeding file not found: {file_path}'))
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)

    def seed_units_of_measure(self, dry_run):
        """Seed units of measure"""
        self.stdout.write('📏 Seeding Units of Measure...')
        
        data = self.load_production_data()
        units_data = data.get('units_of_measure', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(units_data)} units')
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

    def seed_departments(self, dry_run):
        """Seed departments from updated_seeding"""
        self.stdout.write('🏢 Seeding Departments...')
        
        data = self.load_updated_seeding_data('products_and_departments.json')
        if not data:
            return
        
        departments_data = data.get('departments', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(departments_data)} departments')
            return
        
        created_count = 0
        with transaction.atomic():
            for dept_data in departments_data:
                dept, created = Department.objects.get_or_create(
                    name=dept_data['name'],
                    defaults={
                        'description': dept_data.get('description', ''),
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} departments'))

    def seed_products(self, dry_run):
        """Seed products from updated_seeding"""
        self.stdout.write('📦 Seeding Products...')
        
        data = self.load_updated_seeding_data('products_and_departments.json')
        if not data:
            return
        
        products_data = data.get('products', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(products_data)} products')
            return
        
        created_count = 0
        with transaction.atomic():
            for product_data in products_data:
                try:
                    department = Department.objects.get(name=product_data['department'])
                    
                    product, created = Product.objects.get_or_create(
                        name=product_data['name'],
                        defaults={
                            'description': product_data.get('description', ''),
                            'department': department,
                            'price': Decimal(str(product_data.get('price', 0.0))),
                            'unit': product_data.get('unit', 'kg'),
                            'stock_level': product_data.get('stock_level', 0.0),
                            'minimum_stock': product_data.get('minimum_stock', 5.0),
                            'is_active': product_data.get('is_active', True),
                        }
                    )
                    if created:
                        created_count += 1
                except Department.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Department not found: {product_data["department"]}'))
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} products'))

    def seed_suppliers(self, dry_run):
        """Seed suppliers from production data"""
        self.stdout.write('🏭 Seeding Suppliers...')
        
        data = self.load_production_data()
        suppliers_data = data.get('suppliers', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(suppliers_data)} suppliers')
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

    def seed_supplier_products(self, dry_run):
        """Seed supplier products with pricing from updated_seeding"""
        self.stdout.write('💰 Seeding Supplier Products & Pricing...')
        
        data = self.load_updated_seeding_data('suppliers_and_products.json')
        if not data:
            self.stdout.write(self.style.WARNING('No supplier products data found'))
            return
        
        supplier_products_data = data.get('supplier_products', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(supplier_products_data)} supplier products')
            return
        
        created_count = 0
        error_count = 0
        
        with transaction.atomic():
            for sp_data in supplier_products_data:
                try:
                    supplier = Supplier.objects.get(name=sp_data['supplier'])
                    
                    # Handle multiple products with same name by trying to match exactly
                    products = Product.objects.filter(name=sp_data['product'])
                    if products.count() > 1:
                        # Try to find exact match or skip
                        product = products.first()
                    elif products.count() == 1:
                        product = products.first()
                    else:
                        self.stdout.write(self.style.ERROR(f'Product not found: {sp_data["product"]}'))
                        error_count += 1
                        continue
                    
                    sp, created = SupplierProduct.objects.get_or_create(
                        supplier=supplier,
                        product=product,
                        defaults={
                            'supplier_product_code': sp_data.get('supplier_product_code', ''),
                            'supplier_product_name': sp_data.get('supplier_product_name', ''),
                            'supplier_category_code': sp_data.get('supplier_category_code', ''),
                            'supplier_price': Decimal(str(sp_data.get('supplier_price', 0.0))),
                            'currency': sp_data.get('currency', 'ZAR'),
                            'is_available': sp_data.get('is_available', True),
                            'stock_quantity': sp_data.get('stock_quantity'),
                            'minimum_order_quantity': sp_data.get('minimum_order_quantity'),
                            'lead_time_days': sp_data.get('lead_time_days'),
                            'quality_rating': Decimal(str(sp_data['quality_rating'])) if sp_data.get('quality_rating') else None,
                            'last_order_date': sp_data.get('last_order_date'),
                        }
                    )
                    if created:
                        created_count += 1
                        
                except Supplier.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'Supplier not found: {sp_data["supplier"]}'))
                    error_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error creating supplier product: {e}'))
                    error_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} supplier products'))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  {error_count} errors occurred'))

    def seed_users(self, dry_run):
        """Seed users from production data"""
        self.stdout.write('👥 Seeding Users...')
        
        data = self.load_production_data()
        users_data = data.get('users', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(users_data)} users')
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
                    
                    # Create farm profile for staff
                    user_type = user_data.get('user_type', 'private')
                    if user_type in ['admin', 'farm_manager', 'stock_taker']:
                        position_map = {
                            'admin': ('System Administrator', 'admin'),
                            'farm_manager': ('Farm Manager', 'manager'),
                            'stock_taker': ('Stock Controller', 'basic'),
                        }
                        position, access_level = position_map.get(user_type, ('Staff', 'basic'))
                        
                        permissions = {
                            'admin': {'can_manage_inventory': True, 'can_approve_orders': True, 'can_manage_customers': True, 'can_view_reports': True},
                            'farm_manager': {'can_manage_inventory': True, 'can_approve_orders': True, 'can_manage_customers': True, 'can_view_reports': True},
                            'stock_taker': {'can_manage_inventory': True, 'can_approve_orders': False, 'can_manage_customers': False, 'can_view_reports': True},
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

    def seed_customers(self, dry_run):
        """Seed customers from production data"""
        self.stdout.write('🍽️ Seeding Customers...')
        
        data = self.load_production_data()
        customers_data = data.get('customers', {})
        
        total_customers = sum(len(customers) for area, customers in customers_data.items() if area != 'private_customers')
        total_customers += len(customers_data.get('private_customers', []))
        
        if dry_run:
            self.stdout.write(f'    Would create {total_customers} customers')
            return
        
        created_count = 0
        with transaction.atomic():
            # Restaurant customers
            for area, customers in customers_data.items():
                if area == 'private_customers':
                    continue
                    
                for customer_data in customers:
                    user, user_created = User.objects.get_or_create(
                        email=customer_data['email'],
                        defaults={
                            'first_name': customer_data['business_name'],
                            'last_name': 'Restaurant',
                            'phone': customer_data.get('phone', ''),
                            'is_active': True,
                        }
                    )
                    
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
                user, user_created = User.objects.get_or_create(
                    email=customer_data['email'],
                    defaults={
                        'first_name': customer_data.get('customer_name', '').split()[0] if customer_data.get('customer_name') else 'Private',
                        'last_name': 'Customer',
                        'phone': customer_data.get('phone', ''),
                        'is_active': True,
                    }
                )
                
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

    def seed_pricing_rules(self, dry_run):
        """Seed pricing rules from updated_seeding"""
        self.stdout.write('💰 Seeding Pricing Rules...')
        
        data = self.load_updated_seeding_data('pricing_rules.json')
        if not data:
            self.stdout.write(self.style.WARNING('No pricing rules data found'))
            return
        
        pricing_rules_data = data.get('pricing_rules', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(pricing_rules_data)} pricing rules')
            return
        
        created_count = 0
        with transaction.atomic():
            for rule_data in pricing_rules_data:
                rule, created = PricingRule.objects.get_or_create(
                    name=rule_data['name'],
                    defaults={
                        'description': rule_data.get('description', ''),
                        'markup_percentage': Decimal(str(rule_data.get('markup_percentage', 0.0))),
                        'is_active': rule_data.get('is_active', True),
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} pricing rules'))

    def print_summary(self):
        """Print seeding summary"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 PRODUCTION SEEDING SUMMARY'))
        self.stdout.write('='*50)
        
        self.stdout.write(f'👥 Users: {User.objects.count()}')
        self.stdout.write(f'🍽️  Restaurant Profiles: {RestaurantProfile.objects.count()}')
        self.stdout.write(f'👨‍🌾 Farm Profiles: {FarmProfile.objects.count()}')
        self.stdout.write(f'🏠 Private Customers: {PrivateCustomerProfile.objects.count()}')
        self.stdout.write(f'🏭 Suppliers: {Supplier.objects.count()}')
        self.stdout.write(f'💰 Supplier Products: {SupplierProduct.objects.count()}')
        self.stdout.write(f'📦 Products: {Product.objects.count()}')
        self.stdout.write(f'🏢 Departments: {Department.objects.count()}')
        self.stdout.write(f'📏 Units: {UnitOfMeasure.objects.count()}')
        self.stdout.write(f'💲 Pricing Rules: {PricingRule.objects.count()}')
        
        self.stdout.write('\n✅ DATABASE READY FOR PRODUCTION!')
