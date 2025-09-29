from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal
import json
import os


class Command(BaseCommand):
    help = 'Seed products from updated seeding data with all current database products'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products and departments before importing',
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
            self.stdout.write('Clearing existing products and departments...')
            Product.objects.all().delete()
            Department.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing product data cleared.'))

        self.create_departments_from_data(seeding_dir)
        self.create_products_from_data(seeding_dir)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 UPDATED PRODUCT CATALOG SEEDED SUCCESSFULLY!'
            )
        )

    def load_seeding_data(self, seeding_dir):
        """Load seeding data from JSON file"""
        file_path = os.path.join(seeding_dir, 'products_and_departments.json')
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Seeding file not found: {file_path}'))
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)

    def create_departments_from_data(self, seeding_dir):
        """Create departments from updated seeding data"""
        data = self.load_seeding_data(seeding_dir)
        if not data:
            return
        
        departments_data = data.get('departments', [])
        
        self.stdout.write(f'Creating {len(departments_data)} departments...')
        
        with transaction.atomic():
            for dept_data in departments_data:
                department, created = Department.objects.get_or_create(
                    name=dept_data['name'],
                    defaults={
                        'description': dept_data.get('description', ''),
                        'is_active': True,
                    }
                )
                if created:
                    self.stdout.write(f'  ✅ Created department: {department.name}')
                else:
                    self.stdout.write(f'  ℹ️  Department already exists: {department.name}')

    def create_products_from_data(self, seeding_dir):
        """Create products from updated seeding data"""
        data = self.load_seeding_data(seeding_dir)
        if not data:
            return
        
        products_data = data.get('products', [])
        
        self.stdout.write(f'Creating {len(products_data)} products...')
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for product_data in products_data:
                try:
                    department = Department.objects.get(name=product_data['department'])
                    
                    # Use get_or_create with the unique constraint (name, department, unit)
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
                        if created_count <= 10:  # Show first 10 for brevity
                            self.stdout.write(f'  ✅ Created: {product.name} ({product.unit})')
                    else:
                        # Update existing product with current data
                        product.description = product_data.get('description', '')
                        product.price = Decimal(str(product_data['price']))
                        product.stock_level = Decimal(str(product_data['stock_level']))
                        product.minimum_stock = Decimal(str(product_data['minimum_stock']))
                        product.is_active = product_data.get('is_active', True)
                        product.needs_setup = product_data.get('needs_setup', False)
                        product.save()
                        updated_count += 1
                        
                except Department.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f'  Department not found: {product_data["department"]}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error creating product {product_data["name"]}: {e}'))
        
        self.stdout.write(f'  ✅ Created {created_count} new products')
        self.stdout.write(f'  🔄 Updated {updated_count} existing products')
        
        # Show summary by department
        self.stdout.write('\n📊 Products by Department:')
        for dept in Department.objects.all():
            count = Product.objects.filter(department=dept).count()
            self.stdout.write(f'  - {dept.name}: {count} products')
        
        # Show summary by unit
        self.stdout.write('\n📏 Products by Unit:')
        from django.db.models import Count
        unit_counts = Product.objects.values('unit').annotate(count=Count('unit')).order_by('-count')
        for unit_data in unit_counts:
            self.stdout.write(f'  - {unit_data["unit"]}: {unit_data["count"]} products')

        self.stdout.write(f'\n✅ Products seeding completed: {Product.objects.count()} total products')
