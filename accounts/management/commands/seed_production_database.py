"""
Production Database Seeding Command
Seeds the database with current production-ready data from updated seeding files
This ensures consistency and eliminates duplicates for live deployment
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from accounts.models import RestaurantProfile, FarmProfile, PrivateCustomerProfile
from products.models import Product, Department
from suppliers.models import Supplier, SalesRep, SupplierProduct
from inventory.models import PricingRule
from decimal import Decimal
import json
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed production database with current data from updated seeding files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seeding-dir',
            type=str,
            default='updated_seeding',
            help='Directory containing updated seeding files',
        )
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
        seeding_dir = options['seeding_dir']
        clear_existing = options['clear_existing']
        dry_run = options['dry_run']
        
        if not os.path.exists(seeding_dir):
            self.stdout.write(self.style.ERROR(f'Seeding directory {seeding_dir} does not exist'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('=== PRODUCTION DATABASE SEEDING ==='))
        
        if clear_existing and not dry_run:
            self.clear_existing_data()
        
        # Seed in dependency order
        self.seed_departments(seeding_dir, dry_run)
        self.seed_products(seeding_dir, dry_run)
        self.seed_pricing_rules(seeding_dir, dry_run)
        self.seed_users_and_profiles(seeding_dir, dry_run)
        self.seed_suppliers(seeding_dir, dry_run)
        self.seed_sales_reps(seeding_dir, dry_run)
        self.seed_supplier_products(seeding_dir, dry_run)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETED - No actual changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('🎉 PRODUCTION DATABASE SEEDING COMPLETED!'))

    def clear_existing_data(self):
        """Clear existing data (use with extreme caution)"""
        self.stdout.write(self.style.WARNING('⚠️  CLEARING EXISTING DATA...'))
        
        with transaction.atomic():
            # Clear in reverse dependency order
            SupplierProduct.objects.all().delete()
            SalesRep.objects.all().delete()
            Supplier.objects.all().delete()
            
            # Clear profiles first
            RestaurantProfile.objects.all().delete()
            FarmProfile.objects.all().delete()
            PrivateCustomerProfile.objects.all().delete()
            
            # Clear users (except superusers)
            User.objects.filter(is_superuser=False).delete()
            
            PricingRule.objects.all().delete()
            Product.objects.all().delete()
            Department.objects.all().delete()
            
        self.stdout.write(self.style.SUCCESS('✅ Existing data cleared'))

    def load_json_file(self, seeding_dir, filename):
        """Load and return JSON data from file"""
        file_path = os.path.join(seeding_dir, filename)
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)

    def seed_departments(self, seeding_dir, dry_run):
        """Seed departments"""
        self.stdout.write('\n🏢 Seeding Departments...')
        
        data = self.load_json_file(seeding_dir, 'products_and_departments.json')
        if not data:
            return
        
        departments_data = data.get('departments', [])
        
        if dry_run:
            self.stdout.write(f'  Would create {len(departments_data)} departments')
            return
        
        created_count = 0
        with transaction.atomic():
            for dept_data in departments_data:
                department, created = Department.objects.get_or_create(
                    name=dept_data['name'],
                    defaults={
                        'description': dept_data.get('description', ''),
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(f'  ✅ Created {created_count} departments')

    def seed_products(self, seeding_dir, dry_run):
        """Seed products"""
        self.stdout.write('\n🛍️ Seeding Products...')
        
        data = self.load_json_file(seeding_dir, 'products_and_departments.json')
        if not data:
            return
        
        products_data = data.get('products', [])
        
        if dry_run:
            self.stdout.write(f'  Would create {len(products_data)} products')
            return
        
        created_count = 0
        with transaction.atomic():
            for product_data in products_data:
                try:
                    department = Department.objects.get(name=product_data['department'])
                    product, created = Product.objects.get_or_create(
                        name=product_data['name'],
                        department=department,
                        unit=product_data['unit'],
                        defaults={
                            'description': product_data.get('description', ''),
                            'price': Decimal(str(product_data['price'])),
                            'stock_level': Decimal(str(product_data['stock_level'])),
                            'minimum_stock': Decimal(str(product_data['minimum_stock'])),
                            'is_active': product_data.get('is_active', True),
                            'needs_setup': product_data.get('needs_setup', False),
                        }
                    )
                    if created:
                        created_count += 1
                except Department.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  Department not found: {product_data["department"]}'))
        
        self.stdout.write(f'  ✅ Created {created_count} products')

    def seed_pricing_rules(self, seeding_dir, dry_run):
        """Seed pricing rules"""
        self.stdout.write('\n💰 Seeding Pricing Rules...')
        
        data = self.load_json_file(seeding_dir, 'pricing_rules.json')
        if not data:
            return
        
        pricing_rules_data = data.get('pricing_rules', [])
        
        if dry_run:
            self.stdout.write(f'  Would create {len(pricing_rules_data)} pricing rules')
            return
        
        created_count = 0
        with transaction.atomic():
            for rule_data in pricing_rules_data:
                try:
                    # Get or create system user for created_by
                    system_user, _ = User.objects.get_or_create(
                        email='system@fambrifarms.co.za',
                        defaults={
                            'first_name': 'System',
                            'last_name': 'Admin',
                            'user_type': 'admin',
                            'is_staff': True,
                            'is_superuser': True,
                        }
                    )
                    
                    rule, created = PricingRule.objects.get_or_create(
                        name=rule_data['name'],
                        defaults={
                            'description': rule_data.get('description', ''),
                            'customer_segment': rule_data.get('customer_segment', 'standard'),
                            'base_markup_percentage': Decimal(str(rule_data['base_markup_percentage'])),
                            'volatility_adjustment': Decimal(str(rule_data.get('volatility_adjustment', 0))),
                            'minimum_margin_percentage': Decimal(str(rule_data.get('minimum_margin_percentage', 5))),
                            'category_adjustments': rule_data.get('category_adjustments', {}),
                            'trend_multiplier': Decimal(str(rule_data.get('trend_multiplier', 1.0))),
                            'seasonal_adjustment': Decimal(str(rule_data.get('seasonal_adjustment', 0))),
                            'is_active': rule_data.get('is_active', True),
                            'effective_from': rule_data.get('effective_from'),
                            'effective_until': rule_data.get('effective_until'),
                            'created_by': system_user,
                        }
                    )
                    if created:
                        created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error creating pricing rule {rule_data["name"]}: {e}'))
        
        self.stdout.write(f'  ✅ Created {created_count} pricing rules')

    def seed_users_and_profiles(self, seeding_dir, dry_run):
        """Seed users and their profiles"""
        self.stdout.write('\n👥 Seeding Users and Profiles...')
        
        data = self.load_json_file(seeding_dir, 'users_and_profiles.json')
        if not data:
            return
        
        users_data = data.get('users', [])
        restaurant_profiles = data.get('restaurant_profiles', [])
        farm_profiles = data.get('farm_profiles', [])
        private_profiles = data.get('private_profiles', [])
        
        if dry_run:
            self.stdout.write(f'  Would create {len(users_data)} users')
            self.stdout.write(f'  Would create {len(restaurant_profiles)} restaurant profiles')
            self.stdout.write(f'  Would create {len(farm_profiles)} farm profiles')
            self.stdout.write(f'  Would create {len(private_profiles)} private profiles')
            return
        
        users_created = 0
        restaurant_profiles_created = 0
        farm_profiles_created = 0
        private_profiles_created = 0
        
        with transaction.atomic():
            # Create users first
            for user_data in users_data:
                user, created = User.objects.get_or_create(
                    email=user_data['email'],
                    defaults={
                        'first_name': user_data.get('first_name', ''),
                        'last_name': user_data.get('last_name', ''),
                        'user_type': user_data.get('user_type', 'restaurant'),
                        'phone': user_data.get('phone', ''),
                        'is_verified': user_data.get('is_verified', False),
                        'is_active': user_data.get('is_active', True),
                        'is_staff': user_data.get('is_staff', False),
                        'is_superuser': user_data.get('is_superuser', False),
                        'roles': user_data.get('roles', []),
                        'restaurant_roles': user_data.get('restaurant_roles', []),
                    }
                )
                if created:
                    users_created += 1
                    # Set a default password for new users
                    user.set_password('defaultpassword123')
                    user.save()
            
            # Create restaurant profiles
            for profile_data in restaurant_profiles:
                try:
                    user = User.objects.get(email=profile_data['user_email'])
                    
                    # Get preferred pricing rule if specified
                    preferred_rule = None
                    if profile_data.get('preferred_pricing_rule'):
                        try:
                            preferred_rule = PricingRule.objects.get(name=profile_data['preferred_pricing_rule'])
                        except PricingRule.DoesNotExist:
                            pass
                    
                    profile, created = RestaurantProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'business_name': profile_data['business_name'],
                            'branch_name': profile_data.get('branch_name', ''),
                            'business_registration': profile_data.get('business_registration', ''),
                            'address': profile_data.get('address', ''),
                            'city': profile_data.get('city', ''),
                            'postal_code': profile_data.get('postal_code', ''),
                            'payment_terms': profile_data.get('payment_terms', 'Net 30'),
                            'is_private_customer': profile_data.get('is_private_customer', False),
                            'delivery_notes': profile_data.get('delivery_notes', ''),
                            'order_pattern': profile_data.get('order_pattern', ''),
                            'preferred_pricing_rule': preferred_rule,
                        }
                    )
                    if created:
                        restaurant_profiles_created += 1
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  User not found: {profile_data["user_email"]}'))
            
            # Create farm profiles
            for profile_data in farm_profiles:
                try:
                    user = User.objects.get(email=profile_data['user_email'])
                    profile, created = FarmProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'employee_id': profile_data.get('employee_id', ''),
                            'department': profile_data.get('department', ''),
                            'position': profile_data.get('position', ''),
                            'whatsapp_number': profile_data.get('whatsapp_number', ''),
                            'access_level': profile_data.get('access_level', 'basic'),
                            'can_manage_inventory': profile_data.get('can_manage_inventory', False),
                            'can_approve_orders': profile_data.get('can_approve_orders', False),
                            'can_manage_customers': profile_data.get('can_manage_customers', False),
                            'can_view_reports': profile_data.get('can_view_reports', True),
                            'notes': profile_data.get('notes', ''),
                        }
                    )
                    if created:
                        farm_profiles_created += 1
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  User not found: {profile_data["user_email"]}'))
            
            # Create private customer profiles
            for profile_data in private_profiles:
                try:
                    user = User.objects.get(email=profile_data['user_email'])
                    profile, created = PrivateCustomerProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'customer_type': profile_data.get('customer_type', 'household'),
                            'delivery_address': profile_data.get('delivery_address', ''),
                            'delivery_instructions': profile_data.get('delivery_instructions', ''),
                            'preferred_delivery_day': profile_data.get('preferred_delivery_day', 'tuesday'),
                            'whatsapp_number': profile_data.get('whatsapp_number', ''),
                            'credit_limit': Decimal(str(profile_data.get('credit_limit', 1000))),
                            'order_notes': profile_data.get('order_notes', ''),
                        }
                    )
                    if created:
                        private_profiles_created += 1
                except User.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  User not found: {profile_data["user_email"]}'))
        
        self.stdout.write(f'  ✅ Created {users_created} users')
        self.stdout.write(f'  ✅ Created {restaurant_profiles_created} restaurant profiles')
        self.stdout.write(f'  ✅ Created {farm_profiles_created} farm profiles')
        self.stdout.write(f'  ✅ Created {private_profiles_created} private profiles')

    def seed_suppliers(self, seeding_dir, dry_run):
        """Seed suppliers"""
        self.stdout.write('\n🏢 Seeding Suppliers...')
        
        data = self.load_json_file(seeding_dir, 'suppliers_and_products.json')
        if not data:
            return
        
        suppliers_data = data.get('suppliers', [])
        
        if dry_run:
            self.stdout.write(f'  Would create {len(suppliers_data)} suppliers')
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
                        'description': supplier_data.get('description', ''),
                        'supplier_type': supplier_data.get('supplier_type', 'external'),
                        'registration_number': supplier_data.get('registration_number', ''),
                        'tax_number': supplier_data.get('tax_number', ''),
                        'payment_terms_days': supplier_data.get('payment_terms_days', 30),
                        'lead_time_days': supplier_data.get('lead_time_days', 3),
                        'minimum_order_value': Decimal(str(supplier_data['minimum_order_value'])) if supplier_data.get('minimum_order_value') else None,
                        'is_active': supplier_data.get('is_active', True),
                    }
                )
                if created:
                    created_count += 1
        
        self.stdout.write(f'  ✅ Created {created_count} suppliers')

    def seed_sales_reps(self, seeding_dir, dry_run):
        """Seed sales representatives"""
        self.stdout.write('\n👨‍💼 Seeding Sales Representatives...')
        
        data = self.load_json_file(seeding_dir, 'suppliers_and_products.json')
        if not data:
            return
        
        sales_reps_data = data.get('sales_reps', [])
        
        if dry_run:
            self.stdout.write(f'  Would create {len(sales_reps_data)} sales reps')
            return
        
        created_count = 0
        with transaction.atomic():
            for rep_data in sales_reps_data:
                try:
                    supplier = Supplier.objects.get(name=rep_data['supplier'])
                    rep, created = SalesRep.objects.get_or_create(
                        supplier=supplier,
                        email=rep_data['email'],
                        defaults={
                            'name': rep_data['name'],
                            'phone': rep_data.get('phone', ''),
                            'position': rep_data.get('position', ''),
                            'is_active': rep_data.get('is_active', True),
                            'is_primary': rep_data.get('is_primary', False),
                            'total_orders': rep_data.get('total_orders', 0),
                            'last_contact_date': rep_data.get('last_contact_date'),
                        }
                    )
                    if created:
                        created_count += 1
                except Supplier.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  Supplier not found: {rep_data["supplier"]}'))
        
        self.stdout.write(f'  ✅ Created {created_count} sales representatives')

    def seed_supplier_products(self, seeding_dir, dry_run):
        """Seed supplier products"""
        self.stdout.write('\n📦 Seeding Supplier Products...')
        
        data = self.load_json_file(seeding_dir, 'suppliers_and_products.json')
        if not data:
            return
        
        supplier_products_data = data.get('supplier_products', [])
        
        if dry_run:
            self.stdout.write(f'  Would create {len(supplier_products_data)} supplier products')
            return
        
        created_count = 0
        with transaction.atomic():
            for sp_data in supplier_products_data:
                try:
                    supplier = Supplier.objects.get(name=sp_data['supplier'])
                    
                    # Handle products with same name but different units by getting the first one
                    # In production, this should be more specific, but for seeding we'll use the first match
                    products = Product.objects.filter(name=sp_data['product'])
                    if products.count() == 1:
                        product = products.first()
                    elif products.count() > 1:
                        # Multiple products with same name - use first one and log it
                        product = products.first()
                        if created_count < 5:  # Only log first few to avoid spam
                            self.stdout.write(self.style.WARNING(f'  Multiple products found for "{sp_data["product"]}", using first: {product.name} ({product.unit})'))
                    else:
                        raise Product.DoesNotExist(f'No product found with name: {sp_data["product"]}')
                    
                    sp, created = SupplierProduct.objects.get_or_create(
                        supplier=supplier,
                        product=product,
                        defaults={
                            'supplier_product_code': sp_data.get('supplier_product_code', ''),
                            'supplier_product_name': sp_data.get('supplier_product_name', ''),
                            'supplier_category_code': sp_data.get('supplier_category_code', ''),
                            'supplier_price': Decimal(str(sp_data['supplier_price'])),
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
                except (Supplier.DoesNotExist, Product.DoesNotExist, Exception) as e:
                    self.stdout.write(self.style.ERROR(f'  Error: {e} for {sp_data["supplier"]} - {sp_data["product"]}'))
        
        self.stdout.write(f'  ✅ Created {created_count} supplier products')
