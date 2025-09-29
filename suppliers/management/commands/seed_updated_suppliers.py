from django.core.management.base import BaseCommand
from django.db import transaction
from suppliers.models import Supplier, SalesRep, SupplierProduct
from products.models import Product
from decimal import Decimal
import json
import os


class Command(BaseCommand):
    help = 'Seed suppliers from updated seeding data with current database state'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing suppliers before importing',
        )
        parser.add_argument(
            '--seeding-dir',
            type=str,
            default='updated_seeding',
            help='Directory containing updated seeding files',
        )

    def handle(self, *args, **options):
        seeding_dir = options['seeding_dir']
        
        if options['clear']:
            self.stdout.write('Clearing existing suppliers...')
            SupplierProduct.objects.all().delete()
            SalesRep.objects.all().delete()
            Supplier.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing supplier data cleared.'))

        self.create_suppliers_from_data(seeding_dir)
        self.create_sales_reps_from_data(seeding_dir)
        self.create_supplier_products_from_data(seeding_dir)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 UPDATED SUPPLIERS SEEDED SUCCESSFULLY!'
            )
        )

    def load_seeding_data(self, seeding_dir):
        """Load seeding data from JSON file"""
        file_path = os.path.join(seeding_dir, 'suppliers_and_products.json')
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Seeding file not found: {file_path}'))
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)

    def create_suppliers_from_data(self, seeding_dir):
        """Create suppliers from updated seeding data"""
        data = self.load_seeding_data(seeding_dir)
        if not data:
            return
        
        suppliers_data = data.get('suppliers', [])
        
        self.stdout.write(f'Creating {len(suppliers_data)} suppliers...')
        
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
                    self.stdout.write(f'  ✅ Created supplier: {supplier.name}')
                else:
                    self.stdout.write(f'  ℹ️  Supplier already exists: {supplier.name}')
        
        self.stdout.write(f'✅ Created {created_count} new suppliers')

    def create_sales_reps_from_data(self, seeding_dir):
        """Create sales representatives from updated seeding data"""
        data = self.load_seeding_data(seeding_dir)
        if not data:
            return
        
        sales_reps_data = data.get('sales_reps', [])
        
        self.stdout.write(f'Creating {len(sales_reps_data)} sales representatives...')
        
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
                        self.stdout.write(f'  ✅ Created sales rep: {rep.name} ({supplier.name})')
                except Supplier.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  Supplier not found: {rep_data["supplier"]}'))
        
        self.stdout.write(f'✅ Created {created_count} new sales representatives')

    def create_supplier_products_from_data(self, seeding_dir):
        """Create supplier products from updated seeding data"""
        data = self.load_seeding_data(seeding_dir)
        if not data:
            return
        
        supplier_products_data = data.get('supplier_products', [])
        
        self.stdout.write(f'Creating {len(supplier_products_data)} supplier products...')
        
        created_count = 0
        error_count = 0
        
        with transaction.atomic():
            for sp_data in supplier_products_data:
                try:
                    supplier = Supplier.objects.get(name=sp_data['supplier'])
                    product = Product.objects.get(name=sp_data['product'])
                    
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
                        if created_count <= 10:  # Show first 10 for brevity
                            self.stdout.write(f'  ✅ Created: {supplier.name} - {product.name}')
                except (Supplier.DoesNotExist, Product.DoesNotExist) as e:
                    error_count += 1
                    if error_count <= 5:  # Show first 5 errors
                        self.stdout.write(self.style.ERROR(f'  Error: {e} for {sp_data["supplier"]} - {sp_data["product"]}'))
        
        self.stdout.write(f'✅ Created {created_count} new supplier products')
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  {error_count} supplier products had errors'))
        
        # Show summary by supplier
        self.stdout.write('\n📊 Supplier Products Summary:')
        for supplier in Supplier.objects.all():
            count = supplier.supplier_products.count()
            available_count = supplier.supplier_products.filter(is_available=True).count()
            self.stdout.write(f'  - {supplier.name}: {count} products ({available_count} available)')

        self.stdout.write(f'\n✅ Supplier seeding completed: {SupplierProduct.objects.count()} total supplier products')
