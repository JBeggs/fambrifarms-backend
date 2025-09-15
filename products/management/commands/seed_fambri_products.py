from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Seed comprehensive product catalog from real SHALLOME stock data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products and departments before importing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing products and departments...')
            Product.objects.all().delete()
            Department.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing product data cleared.'))

        self.create_departments()
        self.create_comprehensive_products()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 FAMBRI PRODUCT CATALOG SEEDED SUCCESSFULLY!'
            )
        )
        self.stdout.write(f'📊 Product catalog based on real SHALLOME stock data')
        self.stdout.write(f'🌱 Comprehensive inventory from actual farm operations')
        self.stdout.write(f'💰 Realistic pricing based on market rates and WhatsApp data')
        self.stdout.write(f'✅ Phase 4 Complete: Comprehensive product catalog created')

    def create_departments(self):
        """Create product departments based on SHALLOME stock categories"""
        departments_data = [
            {
                'name': 'Vegetables',
                'description': 'Fresh vegetables including root vegetables, leafy greens, and seasonal produce'
            },
            {
                'name': 'Fruits',
                'description': 'Fresh fruits including citrus, berries, melons, and tropical fruits'
            },
            {
                'name': 'Herbs & Spices',
                'description': 'Fresh herbs, spices, and aromatic plants for culinary use'
            },
            {
                'name': 'Mushrooms',
                'description': 'Fresh mushroom varieties for restaurants and specialty cooking'
            },
            {
                'name': 'Specialty Items',
                'description': 'Specialty and premium items including baby vegetables and exotic produce'
            },
        ]

        departments = {}
        for dept_data in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_data['name'],
                defaults={
                    'description': dept_data['description'],
                    'is_active': True
                }
            )
            departments[dept_data['name']] = dept
            if created:
                self.stdout.write(f'📁 Created department: {dept.name}')

        return departments

    def create_comprehensive_products(self):
        """Create comprehensive product catalog from SHALLOME stock data"""
        departments = {dept.name: dept for dept in Department.objects.all()}
        
        # Products extracted from real SHALLOME stock messages (Sep 8-9, 2025)
        products_data = [
            # VEGETABLES - From SHALLOME stock lists
            {'name': 'Beetroot', 'department': 'Vegetables', 'unit': 'kg', 'price': 25.00, 'stock_level': 5.0, 'min_stock': 2.0},
            {'name': 'Butternut', 'department': 'Vegetables', 'unit': 'kg', 'price': 22.00, 'stock_level': 60.0, 'min_stock': 10.0},
            {'name': 'Carrots (Loose)', 'department': 'Vegetables', 'unit': 'kg', 'price': 20.00, 'stock_level': 12.0, 'min_stock': 5.0},
            {'name': 'Carrots (1kg Packed)', 'department': 'Vegetables', 'unit': 'kg', 'price': 22.00, 'stock_level': 24.0, 'min_stock': 10.0},
            {'name': 'Green Cabbage', 'department': 'Vegetables', 'unit': 'head', 'price': 20.00, 'stock_level': 2.0, 'min_stock': 5.0},
            {'name': 'Red Cabbage', 'department': 'Vegetables', 'unit': 'head', 'price': 25.00, 'stock_level': 14.0, 'min_stock': 5.0},
            {'name': 'Cauliflower', 'department': 'Vegetables', 'unit': 'head', 'price': 30.00, 'stock_level': 15.0, 'min_stock': 5.0},
            {'name': 'Broccoli', 'department': 'Vegetables', 'unit': 'head', 'price': 35.00, 'stock_level': 9.0, 'min_stock': 3.0},
            {'name': 'Cucumber', 'department': 'Vegetables', 'unit': 'each', 'price': 8.00, 'stock_level': 47.0, 'min_stock': 10.0},
            {'name': 'Green Chillies', 'department': 'Vegetables', 'unit': 'kg', 'price': 75.00, 'stock_level': 6.9, 'min_stock': 1.0},
            {'name': 'Red Chillies', 'department': 'Vegetables', 'unit': 'kg', 'price': 80.00, 'stock_level': 2.4, 'min_stock': 1.0},
            {'name': 'Green Peppers', 'department': 'Vegetables', 'unit': 'kg', 'price': 40.00, 'stock_level': 8.0, 'min_stock': 2.0},
            {'name': 'Red Peppers', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00, 'stock_level': 3.0, 'min_stock': 2.0},
            {'name': 'Yellow Peppers', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00, 'stock_level': 5.0, 'min_stock': 2.0},
            {'name': 'Mixed Lettuce', 'department': 'Vegetables', 'unit': 'kg', 'price': 40.00, 'stock_level': 3.2, 'min_stock': 2.0},
            {'name': 'Lettuce Head', 'department': 'Vegetables', 'unit': 'head', 'price': 15.00, 'stock_level': 13.0, 'min_stock': 5.0},
            {'name': 'Red Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 18.00, 'stock_level': 3.0, 'min_stock': 5.0},
            {'name': 'White Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 18.00, 'stock_level': 4.0, 'min_stock': 5.0},
            {'name': 'Spring Onions', 'department': 'Vegetables', 'unit': 'kg', 'price': 35.00, 'stock_level': 2.5, 'min_stock': 1.0},
            {'name': 'Potatoes', 'department': 'Vegetables', 'unit': 'bag', 'price': 45.00, 'stock_level': 6.0, 'min_stock': 2.0},
            {'name': 'Sweet Potatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 28.00, 'stock_level': 14.0, 'min_stock': 5.0},
            {'name': 'Tomatoes', 'department': 'Vegetables', 'unit': 'kg', 'price': 25.00, 'stock_level': 5.0, 'min_stock': 3.0},
            {'name': 'Cocktail Tomatoes', 'department': 'Vegetables', 'unit': 'punnet', 'price': 18.00, 'stock_level': 9.0, 'min_stock': 3.0},
            {'name': 'Sweet Corn', 'department': 'Vegetables', 'unit': 'punnet', 'price': 15.00, 'stock_level': 5.0, 'min_stock': 2.0},
            {'name': 'Baby Marrow', 'department': 'Vegetables', 'unit': 'kg', 'price': 30.00, 'stock_level': 11.0, 'min_stock': 3.0},
            {'name': 'Green Beans', 'department': 'Vegetables', 'unit': 'kg', 'price': 45.00, 'stock_level': 3.8, 'min_stock': 2.0},
            {'name': 'Celery', 'department': 'Vegetables', 'unit': 'kg', 'price': 40.00, 'stock_level': 2.5, 'min_stock': 1.0},
            {'name': 'Brussels Sprouts', 'department': 'Vegetables', 'unit': 'kg', 'price': 50.00, 'stock_level': 3.0, 'min_stock': 1.0},

            # FRUITS - From SHALLOME stock lists
            {'name': 'Avocados (Soft)', 'department': 'Fruits', 'unit': 'box', 'price': 120.00, 'stock_level': 2.0, 'min_stock': 1.0},
            {'name': 'Avocados (Hard)', 'department': 'Fruits', 'unit': 'box', 'price': 100.00, 'stock_level': 8.0, 'min_stock': 2.0},
            {'name': 'Avocados (Semi-Ripe)', 'department': 'Fruits', 'unit': 'box', 'price': 110.00, 'stock_level': 3.0, 'min_stock': 1.0},
            {'name': 'Bananas', 'department': 'Fruits', 'unit': 'kg', 'price': 20.00, 'stock_level': 4.0, 'min_stock': 2.0},
            {'name': 'Blueberries', 'department': 'Fruits', 'unit': 'punnet', 'price': 30.00, 'stock_level': 4.0, 'min_stock': 2.0},
            {'name': 'Black Grapes', 'department': 'Fruits', 'unit': 'kg', 'price': 60.00, 'stock_level': 1.0, 'min_stock': 1.0},
            {'name': 'Red Grapes', 'department': 'Fruits', 'unit': 'kg', 'price': 60.00, 'stock_level': 9.0, 'min_stock': 2.0},
            {'name': 'Grapefruit', 'department': 'Fruits', 'unit': 'kg', 'price': 28.00, 'stock_level': 5.0, 'min_stock': 2.0},
            {'name': 'Lemons', 'department': 'Fruits', 'unit': 'kg', 'price': 30.00, 'stock_level': 56.0, 'min_stock': 10.0},
            {'name': 'Oranges', 'department': 'Fruits', 'unit': 'kg', 'price': 25.00, 'stock_level': 0.6, 'min_stock': 2.0},
            {'name': 'Paw Paw', 'department': 'Fruits', 'unit': 'punnet', 'price': 25.00, 'stock_level': 2.0, 'min_stock': 1.0},
            {'name': 'Pineapple', 'department': 'Fruits', 'unit': 'each', 'price': 35.00, 'stock_level': 3.0, 'min_stock': 1.0},
            {'name': 'Strawberries', 'department': 'Fruits', 'unit': 'punnet', 'price': 25.00, 'stock_level': 4.0, 'min_stock': 2.0},
            {'name': 'Sweet Melon', 'department': 'Fruits', 'unit': 'each', 'price': 40.00, 'stock_level': 1.0, 'min_stock': 1.0},
            {'name': 'Water Melon', 'department': 'Fruits', 'unit': 'each', 'price': 50.00, 'stock_level': 1.0, 'min_stock': 1.0},

            # HERBS & SPICES - From SHALLOME stock lists
            {'name': 'Baby Spinach', 'department': 'Herbs & Spices', 'unit': 'kg', 'price': 45.00, 'stock_level': 0.8, 'min_stock': 0.5},
            {'name': 'Basil', 'department': 'Herbs & Spices', 'unit': 'bunch', 'price': 15.00, 'stock_level': 0.2, 'min_stock': 0.1},
            {'name': 'Coriander', 'department': 'Herbs & Spices', 'unit': 'bunch', 'price': 8.00, 'stock_level': 0.6, 'min_stock': 0.2},
            {'name': 'Dill', 'department': 'Herbs & Spices', 'unit': 'bunch', 'price': 15.00, 'stock_level': 0.5, 'min_stock': 0.1},
            {'name': 'Ginger', 'department': 'Herbs & Spices', 'unit': 'kg', 'price': 150.00, 'stock_level': 1.0, 'min_stock': 0.5},
            {'name': 'Mint', 'department': 'Herbs & Spices', 'unit': 'bunch', 'price': 10.00, 'stock_level': 0.5, 'min_stock': 0.2},
            {'name': 'Parsley', 'department': 'Herbs & Spices', 'unit': 'bunch', 'price': 8.00, 'stock_level': 1.7, 'min_stock': 0.5},
            {'name': 'Rocket', 'department': 'Herbs & Spices', 'unit': 'kg', 'price': 120.00, 'stock_level': 4.0, 'min_stock': 1.0},
            {'name': 'Rosemary', 'department': 'Herbs & Spices', 'unit': 'bunch', 'price': 12.00, 'stock_level': 0.3, 'min_stock': 0.1},
            {'name': 'Thyme', 'department': 'Herbs & Spices', 'unit': 'bunch', 'price': 12.00, 'stock_level': 0.5, 'min_stock': 0.1},
            {'name': 'Turmeric', 'department': 'Herbs & Spices', 'unit': 'kg', 'price': 150.00, 'stock_level': 1.0, 'min_stock': 0.5},
            {'name': 'Garlic Cloves', 'department': 'Herbs & Spices', 'unit': 'kg', 'price': 80.00, 'stock_level': 3.5, 'min_stock': 1.0},
            {'name': 'Crushed Garlic', 'department': 'Herbs & Spices', 'unit': 'kg', 'price': 90.00, 'stock_level': 1.0, 'min_stock': 0.5},

            # MUSHROOMS - From SHALLOME stock lists
            {'name': 'Button Mushrooms', 'department': 'Mushrooms', 'unit': 'punnet', 'price': 25.00, 'stock_level': 3.0, 'min_stock': 2.0},
            {'name': 'Brown Mushrooms', 'department': 'Mushrooms', 'unit': 'kg', 'price': 80.00, 'stock_level': 2.0, 'min_stock': 1.0},
            {'name': 'Portabellini Mushrooms', 'department': 'Mushrooms', 'unit': 'kg', 'price': 90.00, 'stock_level': 1.5, 'min_stock': 1.0},

            # SPECIALTY ITEMS - From SHALLOME stock lists
            {'name': 'Baby Corn', 'department': 'Specialty Items', 'unit': 'punnet', 'price': 15.00, 'stock_level': 19.0, 'min_stock': 5.0},
            {'name': 'Cherry Tomatoes', 'department': 'Specialty Items', 'unit': 'punnet', 'price': 20.00, 'stock_level': 5.0, 'min_stock': 3.0},
            {'name': 'Micro Herbs', 'department': 'Specialty Items', 'unit': 'packet', 'price': 25.00, 'stock_level': 10.0, 'min_stock': 3.0},
            {'name': 'Edible Flowers', 'department': 'Specialty Items', 'unit': 'packet', 'price': 35.00, 'stock_level': 5.0, 'min_stock': 2.0},
        ]

        created_count = 0
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                department=departments[product_data['department']],
                defaults={
                    'unit': product_data['unit'],
                    'price': Decimal(str(product_data['price'])),
                    'stock_level': Decimal(str(product_data['stock_level'])),
                    'minimum_stock': Decimal(str(product_data['min_stock'])),
                    'is_active': True,
                    'needs_setup': False,  # These are properly configured
                    'description': f"Fresh {product_data['name'].lower()} from Fambri Farms - {product_data['department'].lower()}"
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f'🌱 Created {created_count} products from real SHALLOME stock data')
        self.stdout.write(f'📊 Products organized into {Department.objects.count()} departments')
        self.stdout.write(f'💰 Pricing based on current market rates and WhatsApp data')
        self.stdout.write(f'📦 Stock levels reflect actual farm inventory (Sep 8-9, 2025)')
