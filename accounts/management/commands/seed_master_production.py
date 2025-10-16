"""
MASTER PRODUCTION SEEDING COMMAND
=================================
This is the ONE AND ONLY seeding command for production.
It replaces ALL 26 scattered seeding commands.

Usage:
    python manage.py seed_master_production --clear-all
    python manage.py seed_master_production --dry-run
"""

import json
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'MASTER production seeding - replaces ALL other seeding commands'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-all',
            action='store_true',
            help='Clear ALL existing data before seeding',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating it',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🚀 MASTER PRODUCTION SEEDING'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        dry_run = options.get('dry_run', False)
        clear_all = options.get('clear_all', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Load production seeding data
        seeding_file = os.path.join('data', 'production_seeding.json')
        if not os.path.exists(seeding_file):
            self.stdout.write(self.style.ERROR(f'❌ Seeding file not found: {seeding_file}'))
            return
        
        with open(seeding_file, 'r') as f:
            data = json.load(f)
        
        self.stdout.write(f'📄 Loaded seeding data from: {seeding_file}')
        
        # Clear existing data if requested
        if clear_all and not dry_run:
            self.clear_all_data()
        
        # Seed everything in the correct order
        self.seed_units_of_measure(data, dry_run)
        self.seed_departments(data, dry_run)
        self.seed_products(data, dry_run)
        self.seed_suppliers(data, dry_run)
        self.seed_users(data, dry_run)
        self.seed_customers_complete(dry_run)
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🎉 MASTER PRODUCTION SEEDING COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def clear_all_data(self):
        """Clear all existing data in reverse dependency order"""
        self.stdout.write(self.style.WARNING('🗑️  CLEARING ALL EXISTING DATA...'))
        
        from orders.models import Order, OrderItem
        from whatsapp.models import WhatsAppMessage
        from accounts.models import RestaurantProfile, PrivateCustomerProfile, FarmProfile
        from suppliers.models import Supplier, SupplierProduct
        from products.models import Product, Department
        from inventory.models import UnitOfMeasure, FinishedInventory, StockMovement
        from settings.models import MessageType, PaymentMethod, UserType
        
        # Clear in reverse dependency order - only core models that exist in production
        models_to_clear = [
            (OrderItem, 'Order Items'),
            (Order, 'Orders'),
            (WhatsAppMessage, 'WhatsApp Messages'),
            (RestaurantProfile, 'Restaurant Profiles'),
            (PrivateCustomerProfile, 'Private Customer Profiles'),
            (FarmProfile, 'Farm Profiles'),
            (SupplierProduct, 'Supplier Products'),
            (Supplier, 'Suppliers'),
            (FinishedInventory, 'Finished Inventory'),
            (StockMovement, 'Stock Movements'),
            (Product, 'Products'),
            (Department, 'Departments'),
            (UnitOfMeasure, 'Units of Measure'),
        ]
        
        # Optional models that may not exist in production
        optional_models = [
            (MessageType, 'Message Types'),
            (PaymentMethod, 'Payment Methods'),
            (UserType, 'User Types'),
        ]
        
        # Clear core models (should always exist)
        for model, name in models_to_clear:
            try:
                count = model.objects.count()
                if count > 0:
                    model.objects.all().delete()
                    self.stdout.write(f'    🗑️  Cleared {count} {name}')
                else:
                    self.stdout.write(f'    ✅ No {name} to clear')
            except Exception as e:
                self.stdout.write(f'    ❌ Error clearing {name}: {str(e)[:50]}...')
        
        # Clear optional models (may not exist in production)
        for model, name in optional_models:
            try:
                count = model.objects.count()
                if count > 0:
                    model.objects.all().delete()
                    self.stdout.write(f'    🗑️  Cleared {count} {name}')
                else:
                    self.stdout.write(f'    ✅ No {name} to clear')
            except Exception as e:
                # Skip tables that don't exist (like settings models on production)
                self.stdout.write(f'    ⚠️  Skipped {name} (table may not exist)')
        
        # Clear users except superusers
        try:
            user_count = User.objects.filter(is_superuser=False).count()
            if user_count > 0:
                User.objects.filter(is_superuser=False).delete()
                self.stdout.write(f'    🗑️  Cleared {user_count} Users (kept superusers)')
            else:
                self.stdout.write(f'    ✅ No non-superuser Users to clear')
        except Exception as e:
            self.stdout.write(f'    ⚠️  Could not clear users: {str(e)[:50]}...')

    def seed_units_of_measure(self, data, dry_run):
        """Seed units of measure"""
        self.stdout.write('📏 Seeding Units of Measure...')
        
        from inventory.models import UnitOfMeasure
        
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
                        'abbreviation': unit_data.get('abbreviation', unit_data['name'][:3]),
                        'is_weight': unit_data.get('category') == 'weight',
                        'base_unit_multiplier': Decimal('1.0'),
                        'is_active': True,
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'    ✅ Created {created_count} units of measure'))

    def seed_departments(self, data, dry_run):
        """Seed departments"""
        self.stdout.write('🏢 Seeding Departments...')
        
        from products.models import Department
        
        departments_data = data.get('departments', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(departments_data)} departments')
            for dept in departments_data:
                self.stdout.write(f'    - {dept["name"]}')
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
        
        self.stdout.write(self.style.SUCCESS(f'    ✅ Created {created_count} departments'))

    def seed_products(self, data, dry_run):
        """Seed products from production data"""
        self.stdout.write('📦 Seeding Products...')
        
        from products.models import Product, Department
        
        products_data = data.get('products', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(products_data)} products')
            for i, product in enumerate(products_data[:5]):
                self.stdout.write(f'    - {product["name"]} ({product.get("unit", "kg")}) - {product.get("department", "Unknown")}')
            if len(products_data) > 5:
                self.stdout.write(f'    ... and {len(products_data) - 5} more')
            return
        
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
        
        self.stdout.write(self.style.SUCCESS(f'    ✅ Created {created_count} products'))

    def seed_suppliers(self, data, dry_run):
        """Seed suppliers from updated_seeding/suppliers_and_products.json"""
        self.stdout.write('🏭 Seeding Suppliers...')
        
        from suppliers.models import Supplier, SupplierProduct
        from products.models import Product
        
        # Load suppliers from updated_seeding file
        suppliers_file = os.path.join('updated_seeding', 'suppliers_and_products.json')
        if not os.path.exists(suppliers_file):
            self.stdout.write(f'    ❌ Suppliers file not found: {suppliers_file}')
            return
        
        with open(suppliers_file, 'r') as f:
            suppliers_data = json.load(f)
        
        suppliers_list = suppliers_data.get('suppliers', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(suppliers_list)} suppliers')
            for supplier in suppliers_list:
                self.stdout.write(f'    - {supplier["name"]}')
            return
        
        created_count = 0
        with transaction.atomic():
            for supplier_data in suppliers_list:
                try:
                    # Handle null minimum_order_value
                    min_order_value = supplier_data.get('minimum_order_value')
                    if min_order_value is None:
                        min_order_value = Decimal('0')
                    else:
                        min_order_value = Decimal(str(min_order_value))
                    
                    supplier, created = Supplier.objects.get_or_create(
                        name=supplier_data['name'],
                        defaults={
                            'contact_person': supplier_data.get('contact_person', ''),
                            'phone': supplier_data.get('phone', ''),
                            'email': supplier_data.get('email', ''),
                            'address': supplier_data.get('address', ''),
                            'description': supplier_data.get('description', ''),
                            'supplier_type': supplier_data.get('supplier_type', 'external'),
                            'registration_number': supplier_data.get('registration_number', ''),
                            'tax_number': supplier_data.get('tax_number', ''),
                            'payment_terms_days': supplier_data.get('payment_terms_days', 30),
                            'lead_time_days': supplier_data.get('lead_time_days', 7),
                            'minimum_order_value': min_order_value,
                            'is_active': supplier_data.get('is_active', True),
                        }
                    )
                    if created:
                        created_count += 1
                        
                except Exception as e:
                    self.stdout.write(f'    ❌ Error creating supplier {supplier_data["name"]}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'    ✅ Created {created_count} suppliers'))
        
        # Also seed supplier products with pricing
        self.seed_supplier_products(suppliers_data, dry_run)
    
    def seed_supplier_products(self, suppliers_data, dry_run):
        """Seed supplier products and pricing"""
        self.stdout.write('💰 Seeding Supplier Products & Pricing...')
        
        from suppliers.models import Supplier, SupplierProduct
        from products.models import Product
        
        supplier_products = suppliers_data.get('supplier_products', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(supplier_products)} supplier products')
            return
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        with transaction.atomic():
            for sp_data in supplier_products:
                try:
                    # Find supplier
                    supplier = Supplier.objects.filter(name=sp_data['supplier']).first()
                    if not supplier:
                        skipped_count += 1
                        continue
                    
                    # Find product by name (try exact match first, then partial)
                    product = Product.objects.filter(name=sp_data['product']).first()
                    if not product:
                        # Try partial match for products like "Aubergine box" -> "Aubergine"
                        product_name = sp_data['product'].replace(' box', '').replace(' bag', '').strip()
                        product = Product.objects.filter(name__icontains=product_name).first()
                    if not product:
                        skipped_count += 1
                        continue
                    
                    supplier_product, created = SupplierProduct.objects.get_or_create(
                        supplier=supplier,
                        product=product,
                        defaults={
                            'supplier_product_code': sp_data.get('supplier_product_code', ''),
                            'supplier_product_name': sp_data.get('supplier_product_name', sp_data.get('product', '')),
                            'supplier_category_code': sp_data.get('supplier_category_code', ''),
                            'supplier_price': Decimal(str(sp_data.get('supplier_price', 0))),
                            'currency': sp_data.get('currency', 'ZAR'),
                            'is_available': sp_data.get('is_available', True),
                            'stock_quantity': sp_data.get('stock_quantity', 0),
                            'minimum_order_quantity': sp_data.get('minimum_order_quantity', 1),
                            'lead_time_days': sp_data.get('lead_time_days', 3),
                            'quality_rating': Decimal(str(sp_data.get('quality_rating', 4.0))),
                        }
                    )
                    if created:
                        created_count += 1
                        
                except Exception as e:
                    error_count += 1
                    product_name = sp_data.get('product', 'Unknown')
                    self.stdout.write(f'    ❌ Error creating supplier product {product_name}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'    ✅ Created {created_count} supplier products (skipped: {skipped_count}, errors: {error_count})'))

    def seed_users(self, data, dry_run):
        """Seed users and farm profiles"""
        self.stdout.write('👥 Seeding Users...')
        
        from accounts.models import FarmProfile
        
        users_data = data.get('users', [])
        
        if dry_run:
            self.stdout.write(f'    Would create {len(users_data)} users')
            for user in users_data:
                self.stdout.write(f'    - {user["email"]} ({user.get("user_type", "unknown")})')
            return
        
        created_count = 0
        with transaction.atomic():
            for user_data in users_data:
                try:
                    user, created = User.objects.get_or_create(
                        email=user_data['email'],
                        defaults={
                            'first_name': user_data.get('first_name', ''),
                            'last_name': user_data.get('last_name', ''),
                            'user_type': user_data.get('user_type', 'restaurant'),
                            'phone': user_data.get('phone', ''),
                            'is_active': user_data.get('is_active', True),
                            'is_staff': user_data.get('is_staff', False),
                            'is_superuser': user_data.get('is_superuser', False),
                        }
                    )
                    
                    if created:
                        # Set password
                        password = user_data.get('password', 'defaultpassword123')
                        user.set_password(password)
                        user.save()
                        
                        # Create farm profile for staff users
                        if user_data.get('user_type') == 'staff':
                            access_level = 'admin' if user_data.get('is_superuser') else 'manager'
                            position = 'Administrator' if user_data.get('is_superuser') else 'Manager'
                            
                            FarmProfile.objects.get_or_create(
                                user=user,
                                defaults={
                                    'employee_id': f'STAFF-{created_count + 1:03d}',
                                    'department': 'Operations',
                                    'position': position,
                                    'whatsapp_number': user_data.get('phone', ''),
                                    'access_level': access_level,
                                    'notes': f'Production seeded staff profile',
                                    'can_manage_inventory': True,
                                    'can_approve_orders': True,
                                    'can_manage_customers': True,
                                    'can_view_reports': True,
                                }
                            )
                        
                        created_count += 1
                        
                except Exception as e:
                    self.stdout.write(f'    ❌ Error creating user {user_data["email"]}: {e}')
        
        self.stdout.write(self.style.SUCCESS(f'    ✅ Created {created_count} users'))

    def seed_customers_complete(self, dry_run):
        """Seed complete customer list using sync_customers_complete command"""
        self.stdout.write('🍽️ Seeding Complete Customer List...')
        
        from django.core.management import call_command
        
        if dry_run:
            self.stdout.write('    Would sync all customers (production + missing)')
            call_command('sync_customers_complete', '--dry-run')
        else:
            self.stdout.write('    Syncing production customers + missing customers...')
            call_command('sync_customers_complete')
        
        self.stdout.write(self.style.SUCCESS('    ✅ Customer sync completed'))
