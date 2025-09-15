from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from inventory.models import FinishedInventory, StockMovement, StockAlert
from products.models import Product
from accounts.models import User


class Command(BaseCommand):
    help = 'Seed realistic stock levels and movements based on SHALLOME data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing stock data before importing',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing stock data...')
            StockAlert.objects.all().delete()
            StockMovement.objects.all().delete()
            FinishedInventory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing stock data cleared.'))

        self.create_finished_inventory()
        self.create_stock_movements()
        self.create_stock_alerts()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 FAMBRI STOCK MANAGEMENT SEEDED SUCCESSFULLY!'
            )
        )
        self.stdout.write(f'📦 Realistic inventory levels based on SHALLOME stock reports')
        self.stdout.write(f'📊 Stock movement history with farm operations context')
        self.stdout.write(f'🚨 Intelligent stock alerts for low inventory items')
        self.stdout.write(f'🔄 Live inventory management system operational')
        self.stdout.write(f'✅ Phase 8 Complete: FAMBRI FARMS DIGITAL TRANSFORMATION COMPLETE!')

    def create_finished_inventory(self):
        """Create realistic finished inventory based on SHALLOME stock data"""
        
        # SHALLOME stock data from WhatsApp messages (Sep 8-9, 2025)
        shallome_stock_data = {
            # Vegetables
            'Beetroot': {'available': 5.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 3.0},
            'Butternut': {'available': 60.0, 'reserved': 5.0, 'minimum': 10.0, 'reorder': 15.0},
            'Carrots (Loose)': {'available': 12.0, 'reserved': 2.0, 'minimum': 5.0, 'reorder': 8.0},
            'Carrots (1kg Packed)': {'available': 24.0, 'reserved': 4.0, 'minimum': 10.0, 'reorder': 15.0},
            'Green Cabbage': {'available': 2.0, 'reserved': 0.0, 'minimum': 5.0, 'reorder': 8.0},  # Low stock
            'Red Cabbage': {'available': 14.0, 'reserved': 2.0, 'minimum': 5.0, 'reorder': 8.0},
            'Cauliflower': {'available': 15.0, 'reserved': 3.0, 'minimum': 5.0, 'reorder': 8.0},
            'Broccoli': {'available': 9.0, 'reserved': 1.0, 'minimum': 3.0, 'reorder': 5.0},
            'Cucumber': {'available': 47.0, 'reserved': 8.0, 'minimum': 10.0, 'reorder': 15.0},
            'Green Chillies': {'available': 6.9, 'reserved': 1.0, 'minimum': 1.0, 'reorder': 2.0},
            'Red Chillies': {'available': 2.4, 'reserved': 0.5, 'minimum': 1.0, 'reorder': 2.0},
            'Green Peppers': {'available': 8.0, 'reserved': 1.5, 'minimum': 2.0, 'reorder': 4.0},
            'Red Peppers': {'available': 3.0, 'reserved': 0.5, 'minimum': 2.0, 'reorder': 4.0},  # Low stock
            'Yellow Peppers': {'available': 5.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},
            'Mixed Lettuce': {'available': 3.2, 'reserved': 0.8, 'minimum': 2.0, 'reorder': 4.0},
            'Lettuce Head': {'available': 13.0, 'reserved': 2.0, 'minimum': 5.0, 'reorder': 8.0},
            'Red Onions': {'available': 3.0, 'reserved': 0.5, 'minimum': 5.0, 'reorder': 8.0},  # Low stock
            'White Onions': {'available': 4.0, 'reserved': 1.0, 'minimum': 5.0, 'reorder': 8.0},  # Low stock
            'Spring Onions': {'available': 2.5, 'reserved': 0.5, 'minimum': 1.0, 'reorder': 2.0},
            'Potatoes': {'available': 6.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},  # Bags
            'Sweet Potatoes': {'available': 14.0, 'reserved': 2.0, 'minimum': 5.0, 'reorder': 8.0},
            'Tomatoes': {'available': 5.0, 'reserved': 1.0, 'minimum': 3.0, 'reorder': 5.0},
            'Cocktail Tomatoes': {'available': 9.0, 'reserved': 1.5, 'minimum': 3.0, 'reorder': 5.0},
            'Sweet Corn': {'available': 5.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},
            'Baby Marrow': {'available': 11.0, 'reserved': 2.0, 'minimum': 3.0, 'reorder': 5.0},
            'Green Beans': {'available': 3.8, 'reserved': 0.8, 'minimum': 2.0, 'reorder': 4.0},
            'Celery': {'available': 2.5, 'reserved': 0.5, 'minimum': 1.0, 'reorder': 2.0},
            'Brussels Sprouts': {'available': 3.0, 'reserved': 0.5, 'minimum': 1.0, 'reorder': 2.0},

            # Fruits
            'Avocados (Soft)': {'available': 2.0, 'reserved': 0.5, 'minimum': 1.0, 'reorder': 2.0},
            'Avocados (Hard)': {'available': 8.0, 'reserved': 1.5, 'minimum': 2.0, 'reorder': 4.0},
            'Avocados (Semi-Ripe)': {'available': 3.0, 'reserved': 0.5, 'minimum': 1.0, 'reorder': 2.0},
            'Bananas': {'available': 4.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},
            'Blueberries': {'available': 4.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},
            'Black Grapes': {'available': 1.0, 'reserved': 0.2, 'minimum': 1.0, 'reorder': 2.0},  # Low stock
            'Red Grapes': {'available': 9.0, 'reserved': 1.5, 'minimum': 2.0, 'reorder': 4.0},
            'Grapefruit': {'available': 5.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},
            'Lemons': {'available': 56.0, 'reserved': 8.0, 'minimum': 10.0, 'reorder': 20.0},  # High stock
            'Oranges': {'available': 0.6, 'reserved': 0.1, 'minimum': 2.0, 'reorder': 4.0},  # Critical low
            'Paw Paw': {'available': 2.0, 'reserved': 0.3, 'minimum': 1.0, 'reorder': 2.0},
            'Pineapple': {'available': 3.0, 'reserved': 0.5, 'minimum': 1.0, 'reorder': 2.0},
            'Strawberries': {'available': 4.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},
            'Sweet Melon': {'available': 1.0, 'reserved': 0.2, 'minimum': 1.0, 'reorder': 2.0},
            'Water Melon': {'available': 1.0, 'reserved': 0.2, 'minimum': 1.0, 'reorder': 2.0},

            # Herbs & Spices
            'Baby Spinach': {'available': 0.8, 'reserved': 0.2, 'minimum': 0.5, 'reorder': 1.0},
            'Basil': {'available': 0.2, 'reserved': 0.05, 'minimum': 0.1, 'reorder': 0.3},  # Low stock
            'Coriander': {'available': 0.6, 'reserved': 0.1, 'minimum': 0.2, 'reorder': 0.5},
            'Dill': {'available': 0.5, 'reserved': 0.1, 'minimum': 0.1, 'reorder': 0.3},
            'Ginger': {'available': 1.0, 'reserved': 0.2, 'minimum': 0.5, 'reorder': 1.0},
            'Mint': {'available': 0.5, 'reserved': 0.1, 'minimum': 0.2, 'reorder': 0.5},
            'Parsley': {'available': 1.7, 'reserved': 0.3, 'minimum': 0.5, 'reorder': 1.0},
            'Rocket': {'available': 4.0, 'reserved': 0.8, 'minimum': 1.0, 'reorder': 2.0},
            'Rosemary': {'available': 0.3, 'reserved': 0.05, 'minimum': 0.1, 'reorder': 0.3},
            'Thyme': {'available': 0.5, 'reserved': 0.1, 'minimum': 0.1, 'reorder': 0.3},
            'Turmeric': {'available': 1.0, 'reserved': 0.2, 'minimum': 0.5, 'reorder': 1.0},
            'Garlic Cloves': {'available': 3.5, 'reserved': 0.7, 'minimum': 1.0, 'reorder': 2.0},
            'Crushed Garlic': {'available': 1.0, 'reserved': 0.2, 'minimum': 0.5, 'reorder': 1.0},

            # Mushrooms
            'Button Mushrooms': {'available': 3.0, 'reserved': 0.5, 'minimum': 2.0, 'reorder': 4.0},
            'Brown Mushrooms': {'available': 2.0, 'reserved': 0.3, 'minimum': 1.0, 'reorder': 2.0},
            'Portabellini Mushrooms': {'available': 1.5, 'reserved': 0.3, 'minimum': 1.0, 'reorder': 2.0},

            # Specialty Items
            'Baby Corn': {'available': 19.0, 'reserved': 3.0, 'minimum': 5.0, 'reorder': 10.0},
            'Cherry Tomatoes': {'available': 5.0, 'reserved': 1.0, 'minimum': 3.0, 'reorder': 5.0},
            'Micro Herbs': {'available': 10.0, 'reserved': 2.0, 'minimum': 3.0, 'reorder': 6.0},
            'Edible Flowers': {'available': 5.0, 'reserved': 1.0, 'minimum': 2.0, 'reorder': 4.0},
        }

        created_count = 0
        for product_name, stock_data in shallome_stock_data.items():
            product = Product.objects.filter(name=product_name).first()
            if not product:
                continue

            # Calculate average cost (simplified - using 70% of selling price)
            average_cost = product.price * Decimal('0.70')

            inventory, created = FinishedInventory.objects.get_or_create(
                product=product,
                defaults={
                    'available_quantity': Decimal(str(stock_data['available'])),
                    'reserved_quantity': Decimal(str(stock_data['reserved'])),
                    'minimum_level': Decimal(str(stock_data['minimum'])),
                    'reorder_level': Decimal(str(stock_data['reorder'])),
                    'average_cost': average_cost
                }
            )

            if created:
                created_count += 1

        self.stdout.write(f'📦 Created {created_count} finished inventory records from SHALLOME data')

    def create_stock_movements(self):
        """Create realistic stock movement history"""
        
        # Get admin user for stock movements
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(user_type='admin').first()
        
        if not admin_user:
            self.stdout.write(self.style.WARNING('No admin user found for stock movements'))
            return

        # Get Hazvinei (Stock Taker) for stock movements
        hazvinei = User.objects.filter(email='hazvinei@fambrifarms.co.za').first()
        stock_user = hazvinei if hazvinei else admin_user

        inventories = FinishedInventory.objects.all()
        created_count = 0

        # Create stock movements for the last 30 days
        for days_ago in range(0, 30, 3):  # Every 3 days
            movement_date = timezone.now() - timedelta(days=days_ago)
            
            # Select random products for movements
            selected_inventories = random.sample(list(inventories), min(10, len(inventories)))
            
            for inventory in selected_inventories:
                # Random movement types based on farm operations
                movement_types = [
                    ('finished_adjust', 'Stock count adjustment'),
                    ('finished_sell', 'Product sold to customer'),
                    ('production', 'Fresh harvest added to inventory'),
                    ('finished_waste', 'Spoilage/waste removal'),
                ]
                
                movement_type, description = random.choice(movement_types)
                
                # Generate realistic quantities based on movement type
                if movement_type == 'production':
                    # Fresh harvest - positive quantity
                    quantity = Decimal(str(random.uniform(5.0, 20.0)))
                elif movement_type == 'finished_sell':
                    # Sales - negative quantity
                    quantity = -Decimal(str(random.uniform(1.0, 8.0)))
                elif movement_type == 'finished_waste':
                    # Waste - negative quantity (small amounts)
                    quantity = -Decimal(str(random.uniform(0.1, 2.0)))
                else:
                    # Adjustments - can be positive or negative
                    quantity = Decimal(str(random.uniform(-3.0, 5.0)))

                # Create stock movement
                StockMovement.objects.create(
                    movement_type=movement_type,
                    reference_number=f'SM-{movement_date.strftime("%Y%m%d")}-{random.randint(1000, 9999)}',
                    product=inventory.product,
                    quantity=quantity.quantize(Decimal('0.01')),
                    unit_cost=inventory.average_cost,
                    total_value=(quantity * inventory.average_cost).quantize(Decimal('0.01')),
                    user=stock_user,
                    timestamp=movement_date,
                    notes=f'{description} - {inventory.product.name}'
                )
                
                created_count += 1

        self.stdout.write(f'📊 Created {created_count} stock movement records')

    def create_stock_alerts(self):
        """Create intelligent stock alerts based on current levels"""
        
        # Get Hazvinei (Stock Taker) for alerts
        hazvinei = User.objects.filter(email='hazvinei@fambrifarms.co.za').first()
        
        inventories = FinishedInventory.objects.all()
        created_count = 0

        for inventory in inventories:
            alerts_to_create = []
            
            # Check for low stock
            if inventory.available_quantity <= inventory.minimum_level:
                if inventory.available_quantity <= 0:
                    alert_type = 'out_of_stock'
                    severity = 'critical'
                    message = f'{inventory.product.name} is OUT OF STOCK! Available: {inventory.available_quantity}{inventory.product.unit}'
                else:
                    alert_type = 'low_stock'
                    severity = 'high' if inventory.available_quantity <= (inventory.minimum_level * Decimal('0.5')) else 'medium'
                    message = f'{inventory.product.name} is running low. Available: {inventory.available_quantity}{inventory.product.unit}, Minimum: {inventory.minimum_level}{inventory.product.unit}'
                
                alerts_to_create.append((alert_type, severity, message))
            
            # Check for production needed
            if inventory.needs_production:
                alerts_to_create.append((
                    'production_needed',
                    'medium',
                    f'{inventory.product.name} needs production. Current: {inventory.available_quantity}{inventory.product.unit}, Reorder level: {inventory.reorder_level}{inventory.product.unit}'
                ))
            
            # Check for overstock (more than 3x reorder level)
            if inventory.available_quantity > (inventory.reorder_level * 3):
                alerts_to_create.append((
                    'overstock',
                    'low',
                    f'{inventory.product.name} may be overstocked. Available: {inventory.available_quantity}{inventory.product.unit}, Reorder level: {inventory.reorder_level}{inventory.product.unit}'
                ))

            # Create alerts
            for alert_type, severity, message in alerts_to_create:
                StockAlert.objects.create(
                    alert_type=alert_type,
                    product=inventory.product,
                    message=message,
                    severity=severity,
                    is_active=True
                )
                created_count += 1

        self.stdout.write(f'🚨 Created {created_count} intelligent stock alerts')
        
        # Show critical alerts
        critical_alerts = StockAlert.objects.filter(severity='critical', is_active=True)
        if critical_alerts.exists():
            self.stdout.write(f'⚠️  CRITICAL ALERTS:')
            for alert in critical_alerts:
                self.stdout.write(f'   🔴 {alert.message}')
        
        high_alerts = StockAlert.objects.filter(severity='high', is_active=True)
        if high_alerts.exists():
            self.stdout.write(f'⚠️  HIGH PRIORITY ALERTS: {high_alerts.count()} items need attention')
