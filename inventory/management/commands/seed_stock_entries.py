"""
Django management command to seed stock entries based on orders and market data
Creates realistic stock taking entries for Flutter stock management interface
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from inventory.models import FinishedInventory, StockMovement, StockAlert
from products.models import Product
from orders.models import Order, OrderItem
from accounts.models import User
from whatsapp.models import StockUpdate


class Command(BaseCommand):
    help = 'Seed stock entries based on orders and market data for Flutter interface'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing stock data before seeding',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of stock history to create (default: 30)',
        )
        parser.add_argument(
            '--market-based',
            action='store_true',
            help='Create stock entries based on market/supplier data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('🗑️  Clearing existing stock data...')
            StockAlert.objects.all().delete()
            StockMovement.objects.all().delete()
            FinishedInventory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Existing stock data cleared.'))

        days = options['days']
        market_based = options['market_based']

        self.stdout.write(f'📦 Creating stock entries for {days} days...')
        
        if market_based:
            self.create_market_based_stock()
        else:
            self.create_order_based_stock(days)
        
        self.create_stock_alerts()
        self.create_stock_movements(days)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 STOCK ENTRY SEEDING COMPLETED!'
            )
        )
        self.stdout.write(f'📊 Stock data created for {days} days')
        self.stdout.write(f'🏪 {"Market-based" if market_based else "Order-based"} stock levels')
        self.stdout.write(f'📱 Ready for Flutter stock entry interface')

    def create_order_based_stock(self, days):
        """Create stock entries based on actual orders in the system"""
        self.stdout.write('📋 Creating order-based stock entries...')
        
        # Get all products that have been ordered
        ordered_products = Product.objects.filter(
            orderitem__isnull=False
        ).distinct()
        
        created_count = 0
        
        for product in ordered_products:
            # Calculate demand from recent orders
            recent_orders = OrderItem.objects.filter(
                product=product,
                order__order_date__gte=date.today() - timedelta(days=days)
            )
            
            total_demand = sum(item.quantity for item in recent_orders)
            avg_daily_demand = total_demand / days if days > 0 else 0
            
            # Calculate realistic stock levels
            current_stock = self.calculate_realistic_stock(product, avg_daily_demand)
            minimum_stock = max(avg_daily_demand * 3, 5)  # 3 days buffer minimum
            reorder_level = minimum_stock * 1.5
            
            # Create or update finished inventory
            inventory, created = FinishedInventory.objects.get_or_create(
                product=product,
                defaults={
                    'available_quantity': current_stock,
                    'reserved_quantity': Decimal('0'),
                    'minimum_level': minimum_stock,
                    'reorder_level': reorder_level,
                    'average_cost': product.price * Decimal('0.7'),  # Assume 30% markup
                }
            )
            
            if not created:
                inventory.available_quantity = current_stock
                inventory.minimum_level = minimum_stock
                inventory.reorder_level = reorder_level
                inventory.save()
            
            created_count += 1
            
            if created_count % 10 == 0:
                self.stdout.write(f'  📦 Created {created_count} stock entries...')
        
        self.stdout.write(f'✅ Created {created_count} order-based stock entries')

    def create_market_based_stock(self):
        """Create stock entries based on market/supplier data (SHALLOME)"""
        self.stdout.write('🏪 Creating market-based stock entries...')
        
        # Use SHALLOME stock data from WhatsApp messages
        stock_updates = StockUpdate.objects.all()
        created_count = 0
        
        if stock_updates.exists():
            self.stdout.write(f'📱 Found {stock_updates.count()} WhatsApp stock updates')
            
            for stock_update in stock_updates:
                for product_name, item_data in stock_update.items.items():
                    # Try to find matching product
                    product = self.find_or_create_product(product_name)
                    
                    if product:
                        quantity = Decimal(str(item_data.get('quantity', 0)))
                        
                        # Create realistic stock levels based on market data
                        current_stock = quantity * Decimal(str(random.uniform(0.7, 1.3)))  # ±30% variation
                        minimum_stock = quantity * Decimal('0.2')  # 20% of market stock
                        reorder_level = quantity * Decimal('0.4')  # 40% of market stock
                        
                        inventory, created = FinishedInventory.objects.get_or_create(
                            product=product,
                            defaults={
                                'available_quantity': current_stock,
                                'reserved_quantity': Decimal('0'),
                                'minimum_level': minimum_stock,
                                'reorder_level': reorder_level,
                                'average_cost': product.price * Decimal('0.75'),
                            }
                        )
                        
                        if not created:
                            inventory.available_quantity = current_stock
                            inventory.minimum_level = minimum_stock
                            inventory.reorder_level = reorder_level
                            inventory.save()
                        
                        created_count += 1
        
        # Fallback to default market data if no WhatsApp updates
        if created_count == 0:
            self.create_default_market_stock()
            created_count = Product.objects.count()
        
        self.stdout.write(f'✅ Created {created_count} market-based stock entries')

    def create_default_market_stock(self):
        """Create default market-based stock for all products"""
        self.stdout.write('🏪 Creating default market stock data...')
        
        # Market-based stock levels for common products
        market_stock_data = {
            # Vegetables (high turnover)
            'vegetables': {'base_stock': 50, 'min_ratio': 0.2, 'reorder_ratio': 0.4},
            # Fruits (medium turnover)
            'fruits': {'base_stock': 30, 'min_ratio': 0.25, 'reorder_ratio': 0.45},
            # Herbs (low stock, high value)
            'herbs': {'base_stock': 10, 'min_ratio': 0.3, 'reorder_ratio': 0.5},
            # Default
            'default': {'base_stock': 25, 'min_ratio': 0.25, 'reorder_ratio': 0.4},
        }
        
        for product in Product.objects.all():
            # Determine category
            category = 'default'
            if product.department:
                dept_name = product.department.name.lower()
                if 'vegetable' in dept_name:
                    category = 'vegetables'
                elif 'fruit' in dept_name:
                    category = 'fruits'
                elif 'herb' in dept_name or 'spice' in dept_name:
                    category = 'herbs'
            
            stock_config = market_stock_data[category]
            base_stock = Decimal(str(stock_config['base_stock']))
            
            # Add randomization
            current_stock = base_stock * Decimal(str(random.uniform(0.5, 1.5)))
            minimum_stock = current_stock * Decimal(str(stock_config['min_ratio']))
            reorder_level = current_stock * Decimal(str(stock_config['reorder_ratio']))
            
            FinishedInventory.objects.get_or_create(
                product=product,
                defaults={
                    'available_quantity': current_stock,
                    'reserved_quantity': Decimal('0'),
                    'minimum_level': minimum_stock,
                    'reorder_level': reorder_level,
                    'average_cost': product.price * Decimal('0.75'),
                }
            )

    def calculate_realistic_stock(self, product, avg_daily_demand):
        """Calculate realistic stock levels based on demand patterns"""
        if avg_daily_demand == 0:
            # No recent demand, use conservative stock
            return Decimal(str(random.uniform(10, 50)))
        
        # Stock should cover 5-15 days of demand
        days_coverage = random.uniform(5, 15)
        base_stock = Decimal(str(avg_daily_demand * days_coverage))
        
        # Add randomization (±40%)
        variation = random.uniform(0.6, 1.4)
        return base_stock * Decimal(str(variation))

    def find_or_create_product(self, product_name):
        """Find existing product or create new one"""
        # Try exact match first
        product = Product.objects.filter(name__iexact=product_name).first()
        if product:
            return product
        
        # Try partial match
        product = Product.objects.filter(name__icontains=product_name).first()
        if product:
            return product
        
        # Create new product if not found
        try:
            from products.models import Department
            default_dept = Department.objects.first()
            
            product = Product.objects.create(
                name=product_name,
                price=Decimal('25.00'),  # Default price
                department=default_dept,
                is_active=True,
                description=f'Auto-created from stock data: {product_name}'
            )
            return product
        except Exception as e:
            self.stdout.write(f'⚠️  Could not create product {product_name}: {e}')
            return None

    def create_stock_movements(self, days):
        """Create realistic stock movements for the past period"""
        self.stdout.write('📊 Creating stock movement history...')
        
        movement_types = [
            ('stock_take', 'Stock Take Adjustment'),
            ('receipt', 'Stock Receipt'),
            ('sale', 'Sale/Order Fulfillment'),
            ('adjustment', 'Manual Adjustment'),
            ('waste', 'Waste/Spoilage'),
        ]
        
        inventories = FinishedInventory.objects.all()
        movements_created = 0
        
        for inventory in inventories:
            # Create 2-5 movements per product over the period
            num_movements = random.randint(2, 5)
            
            for i in range(num_movements):
                movement_date = date.today() - timedelta(
                    days=random.randint(1, days)
                )
                
                movement_type, description = random.choice(movement_types)
                
                # Calculate movement quantity based on type
                if movement_type == 'receipt':
                    quantity = Decimal(str(random.uniform(10, 100)))
                elif movement_type == 'sale':
                    quantity = -Decimal(str(random.uniform(5, 50)))
                elif movement_type == 'waste':
                    quantity = -Decimal(str(random.uniform(1, 10)))
                else:  # adjustments, stock_take
                    quantity = Decimal(str(random.uniform(-20, 20)))
                
                # Map movement types to valid choices
                movement_type_mapping = {
                    'stock_take': 'finished_adjust',
                    'receipt': 'finished_adjust', 
                    'sale': 'finished_sell',
                    'adjustment': 'finished_adjust',
                    'waste': 'finished_waste',
                }
                
                mapped_movement_type = movement_type_mapping.get(movement_type, 'finished_adjust')
                
                StockMovement.objects.create(
                    product=inventory.product,
                    movement_type=mapped_movement_type,
                    quantity=quantity,
                    unit_cost=inventory.average_cost or inventory.product.price,
                    total_value=quantity * (inventory.average_cost or inventory.product.price),
                    reference_number=f'SM-{movement_date.strftime("%Y%m%d")}-{random.randint(1000, 9999)}',
                    notes=f'{description} - {movement_date.strftime("%B %d, %Y")}',
                    user=User.objects.filter(is_staff=True).first(),
                )
                movements_created += 1
        
        self.stdout.write(f'✅ Created {movements_created} stock movements')

    def create_stock_alerts(self):
        """Create stock alerts for low inventory items"""
        self.stdout.write('🚨 Creating stock alerts...')
        
        alerts_created = 0
        
        for inventory in FinishedInventory.objects.all():
            # Create alert if stock is below minimum level
            if inventory.available_quantity and inventory.minimum_level:
                if inventory.available_quantity <= inventory.minimum_level:
                    alert_type = 'out_of_stock' if inventory.available_quantity <= 0 else 'low_stock'
                    
                    StockAlert.objects.get_or_create(
                        product=inventory.product,
                        alert_type=alert_type,
                        defaults={
                            'message': f'{inventory.product.name} is {"out of stock" if alert_type == "out_of_stock" else "running low"}',
                            'current_stock': inventory.available_quantity,
                            'minimum_stock': inventory.minimum_level,
                            'is_resolved': False,
                        }
                    )
                    alerts_created += 1
        
        self.stdout.write(f'✅ Created {alerts_created} stock alerts')
