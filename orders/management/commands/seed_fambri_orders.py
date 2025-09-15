from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import random

from orders.models import Order, OrderItem
from accounts.models import User
from products.models import Product
from inventory.models import CustomerPriceListItem


class Command(BaseCommand):
    help = 'Seed realistic order history based on WhatsApp message patterns'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing orders before importing',
        )
        parser.add_argument(
            '--weeks',
            type=int,
            default=8,
            help='Number of weeks of order history to generate (default: 8)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing orders...')
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing order data cleared.'))

        weeks_to_generate = options['weeks']
        self.create_realistic_order_history(weeks_to_generate)

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 FAMBRI ORDER HISTORY SEEDED SUCCESSFULLY!'
            )
        )
        self.stdout.write(f'📅 Generated {weeks_to_generate} weeks of realistic order history')
        self.stdout.write(f'🔄 Tuesday/Thursday order cycles with authentic patterns')
        self.stdout.write(f'📊 Customer-specific ordering behaviors from WhatsApp data')
        self.stdout.write(f'💰 Real pricing and quantities based on actual messages')
        self.stdout.write(f'✅ Phase 7 Complete: Order history system operational')

    def create_realistic_order_history(self, weeks):
        """Create realistic order history based on WhatsApp patterns"""
        
        # Get all customers and their order patterns
        customers_with_patterns = self.get_customer_order_patterns()
        
        if not customers_with_patterns:
            self.stdout.write(self.style.WARNING('No customers found for order generation'))
            return
        
        total_orders_created = 0
        total_items_created = 0
        
        # Generate orders for the specified number of weeks
        start_date = date.today() - timedelta(weeks=weeks)
        
        for week in range(weeks):
            week_start = start_date + timedelta(weeks=week)
            
            # Find Tuesday and Thursday of this week
            tuesday = week_start + timedelta(days=(1 - week_start.weekday()) % 7)  # Tuesday
            thursday = week_start + timedelta(days=(3 - week_start.weekday()) % 7)  # Thursday
            
            # Ensure we don't create future orders
            order_days = []
            if tuesday <= date.today():
                order_days.append(tuesday)
            if thursday <= date.today():
                order_days.append(thursday)
            
            for order_day in order_days:
                # Create orders for this day
                day_orders, day_items = self.create_orders_for_day(order_day, customers_with_patterns)
                total_orders_created += day_orders
                total_items_created += day_items
                
                self.stdout.write(f'📅 {order_day.strftime("%A %Y-%m-%d")}: {day_orders} orders, {day_items} items')
        
        self.stdout.write(f'\n📊 TOTAL: {total_orders_created} orders with {total_items_created} items across {weeks} weeks')

    def get_customer_order_patterns(self):
        """Get customers with their realistic order patterns from WhatsApp data"""
        
        patterns = {
            # Premium Restaurants - Large, detailed orders
            'Casa Bella': {
                'frequency': 0.8,  # 80% chance to order each cycle
                'avg_items': 12,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Mixed Lettuce', 'qty_range': (2, 5), 'unit': 'kg'},
                    {'name': 'Basil', 'qty_range': (3, 6), 'unit': 'bunch'},
                    {'name': 'Cherry Tomatoes', 'qty_range': (5, 10), 'unit': 'punnet'},
                    {'name': 'Rocket', 'qty_range': (1, 3), 'unit': 'kg'},
                    {'name': 'Parsley', 'qty_range': (2, 4), 'unit': 'bunch'},
                    {'name': 'Avocados (Soft)', 'qty_range': (1, 2), 'unit': 'box'},
                    {'name': 'Red Peppers', 'qty_range': (2, 4), 'unit': 'kg'},
                    {'name': 'Yellow Peppers', 'qty_range': (2, 4), 'unit': 'kg'},
                ]
            },
            
            'Maltos': {
                'frequency': 0.9,  # Very regular customer
                'avg_items': 15,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Broccoli', 'qty_range': (8, 12), 'unit': 'head'},
                    {'name': 'Cauliflower', 'qty_range': (8, 12), 'unit': 'head'},
                    {'name': 'Tomatoes', 'qty_range': (1, 2), 'unit': 'box'},
                    {'name': 'Avocados (Semi-Ripe)', 'qty_range': (3, 6), 'unit': 'box'},
                    {'name': 'Butternut', 'qty_range': (3, 6), 'unit': 'kg'},
                    {'name': 'Baby Spinach', 'qty_range': (2, 4), 'unit': 'kg'},
                    {'name': 'Parsley', 'qty_range': (3, 5), 'unit': 'bunch'},
                    {'name': 'Rocket', 'qty_range': (2, 4), 'unit': 'kg'},
                    {'name': 'Potatoes', 'qty_range': (3, 6), 'unit': 'bag'},
                    {'name': 'Lemons', 'qty_range': (3, 6), 'unit': 'kg'},
                    {'name': 'Carrots (1kg Packed)', 'qty_range': (8, 12), 'unit': 'kg'},
                    {'name': 'Cucumber', 'qty_range': (8, 15), 'unit': 'each'},
                    {'name': 'Strawberries', 'qty_range': (4, 6), 'unit': 'punnet'},
                    {'name': 'Mint', 'qty_range': (4, 6), 'unit': 'bunch'},
                    {'name': 'Red Onions', 'qty_range': (1, 3), 'unit': 'bag'},
                ]
            },
            
            'Pecanwood Golf Estate': {
                'frequency': 0.7,
                'avg_items': 20,  # Large institutional orders
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Carrots (Loose)', 'qty_range': (15, 25), 'unit': 'kg'},
                    {'name': 'Butternut', 'qty_range': (10, 20), 'unit': 'kg'},
                    {'name': 'Red Onions', 'qty_range': (8, 15), 'unit': 'bag'},
                    {'name': 'White Onions', 'qty_range': (5, 10), 'unit': 'bag'},
                    {'name': 'Potatoes', 'qty_range': (5, 8), 'unit': 'bag'},
                    {'name': 'Tomatoes', 'qty_range': (4, 8), 'unit': 'box'},
                    {'name': 'Sweet Potatoes', 'qty_range': (15, 25), 'unit': 'kg'},
                    {'name': 'Ginger', 'qty_range': (1, 2), 'unit': 'box'},
                    {'name': 'Garlic Cloves', 'qty_range': (1, 2), 'unit': 'box'},
                    {'name': 'Baby Marrow', 'qty_range': (2, 4), 'unit': 'box'},
                    {'name': 'Green Beans', 'qty_range': (1, 2), 'unit': 'box'},
                    {'name': 'Red Peppers', 'qty_range': (4, 8), 'unit': 'box'},
                    {'name': 'Yellow Peppers', 'qty_range': (2, 4), 'unit': 'box'},
                    {'name': 'Green Peppers', 'qty_range': (2, 4), 'unit': 'box'},
                    {'name': 'Red Chillies', 'qty_range': (1, 2), 'unit': 'box'},
                    {'name': 'Green Chillies', 'qty_range': (1, 2), 'unit': 'box'},
                ]
            },
            
            'Mugg and Bean': {
                'frequency': 0.8,
                'avg_items': 10,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Potatoes', 'qty_range': (25, 35), 'unit': 'kg'},  # "30kg potato"
                    {'name': 'Red Onions', 'qty_range': (15, 25), 'unit': 'kg'},  # "20kg red onion"
                    {'name': 'Sweet Potatoes', 'qty_range': (5, 10), 'unit': 'kg'},
                    {'name': 'Butternut', 'qty_range': (2, 4), 'unit': 'kg'},
                    {'name': 'Lemons', 'qty_range': (12, 18), 'unit': 'kg'},
                    {'name': 'Tomatoes', 'qty_range': (3, 5), 'unit': 'kg'},
                    {'name': 'Red Peppers', 'qty_range': (4, 6), 'unit': 'kg'},
                    {'name': 'Carrots (1kg Packed)', 'qty_range': (4, 6), 'unit': 'kg'},
                    {'name': 'Baby Marrow', 'qty_range': (5, 8), 'unit': 'kg'},
                    {'name': 'Celery', 'qty_range': (3, 5), 'unit': 'kg'},
                ]
            },
            
            # Standard Restaurants
            'T-junction': {
                'frequency': 0.7,
                'avg_items': 8,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Mixed Lettuce', 'qty_range': (15, 25), 'unit': 'kg'},  # "20 kg onions"
                    {'name': 'Red Onions', 'qty_range': (15, 25), 'unit': 'kg'},
                    {'name': 'Lettuce Head', 'qty_range': (10, 20), 'unit': 'head'},
                    {'name': 'Parsley', 'qty_range': (150, 250), 'unit': 'g'},  # "200g Parsley"
                    {'name': 'Chives', 'qty_range': (80, 120), 'unit': 'g'},   # "100g Chives"
                ]
            },
            
            'Venue': {
                'frequency': 0.6,
                'avg_items': 6,
                'preferred_day': 'thursday',  # Event catering
                'typical_products': [
                    {'name': 'Tomatoes', 'qty_range': (4, 6), 'unit': 'kg'},
                    {'name': 'Button Mushrooms', 'qty_range': (4, 6), 'unit': 'kg'},
                    {'name': 'White Onions', 'qty_range': (8, 12), 'unit': 'kg'},
                ]
            },
            
            # Budget Establishments
            'Debonair Pizza': {
                'frequency': 0.6,
                'avg_items': 5,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Tomatoes', 'qty_range': (4, 6), 'unit': 'kg'},
                    {'name': 'Button Mushrooms', 'qty_range': (4, 6), 'unit': 'kg'},
                    {'name': 'White Onions', 'qty_range': (8, 12), 'unit': 'kg'},
                    {'name': 'Green Peppers', 'qty_range': (2, 4), 'unit': 'kg'},
                    {'name': 'Red Peppers', 'qty_range': (1, 3), 'unit': 'kg'},
                ]
            },
            
            'Barchef Entertainment': {
                'frequency': 0.5,
                'avg_items': 6,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Lemons', 'qty_range': (1, 2), 'unit': 'box'},
                    {'name': 'Strawberries', 'qty_range': (3, 5), 'unit': 'punnet'},
                    {'name': 'Mint', 'qty_range': (3, 5), 'unit': 'bunch'},
                    {'name': 'Rosemary', 'qty_range': (1, 3), 'unit': 'bunch'},
                    {'name': 'Basil', 'qty_range': (1, 2), 'unit': 'bunch'},
                ]
            },
            
            # Private Customers
            'Sylvia': {
                'frequency': 0.8,  # Regular Tuesday orders
                'avg_items': 4,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Potatoes', 'qty_range': (2, 3), 'unit': 'kg'},  # "Potato 2 x 1kg"
                    {'name': 'Oranges', 'qty_range': (1, 2), 'unit': 'kg'},
                    {'name': 'Bananas', 'qty_range': (2, 3), 'unit': 'kg'},   # "Banana 2 x 1kg"
                    {'name': 'Carrots (1kg Packed)', 'qty_range': (1, 2), 'unit': 'kg'},
                ]
            },
            
            'Marco': {
                'frequency': 0.6,
                'avg_items': 6,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Mixed Lettuce', 'qty_range': (1, 2), 'unit': 'kg'},
                    {'name': 'Tomatoes', 'qty_range': (2, 4), 'unit': 'kg'},
                    {'name': 'Cucumber', 'qty_range': (5, 10), 'unit': 'each'},
                    {'name': 'Avocados (Hard)', 'qty_range': (3, 6), 'unit': 'each'},
                    {'name': 'Lemons', 'qty_range': (1, 2), 'unit': 'kg'},
                    {'name': 'Carrots (Loose)', 'qty_range': (2, 3), 'unit': 'kg'},
                ]
            },
            
            'Arthur': {
                'frequency': 0.4,
                'avg_items': 2,
                'preferred_day': 'tuesday',
                'typical_products': [
                    {'name': 'Mixed Lettuce', 'qty_range': (2, 3), 'unit': 'box'},  # "Arthur box x2"
                    {'name': 'Tomatoes', 'qty_range': (1, 2), 'unit': 'box'},
                ]
            },
        }
        
        # Match patterns to actual users
        customer_patterns = {}
        for customer_name, pattern in patterns.items():
            # Find user by business name or first name
            user = User.objects.filter(
                restaurantprofile__business_name__icontains=customer_name
            ).first()
            
            if not user:
                user = User.objects.filter(
                    first_name__icontains=customer_name.split()[0]
                ).first()
            
            if user:
                customer_patterns[user] = pattern
                
        return customer_patterns

    def create_orders_for_day(self, order_day, customers_with_patterns):
        """Create orders for a specific day based on customer patterns"""
        orders_created = 0
        items_created = 0
        
        day_name = order_day.strftime('%A').lower()
        
        for customer, pattern in customers_with_patterns.items():
            # Check if customer orders on this day
            preferred_day = pattern.get('preferred_day', 'tuesday')
            frequency = pattern.get('frequency', 0.5)
            
            # Adjust frequency based on day preference
            if day_name == preferred_day:
                order_probability = frequency
            else:
                order_probability = frequency * 0.3  # 30% chance on non-preferred days
            
            # Random decision to place order
            if random.random() > order_probability:
                continue
            
            # Create order
            order = self.create_order_for_customer(customer, order_day, pattern)
            if order:
                orders_created += 1
                items_created += order.items.count()
        
        return orders_created, items_created

    def create_order_for_customer(self, customer, order_day, pattern):
        """Create a realistic order for a specific customer"""
        
        try:
            with transaction.atomic():
                # Calculate delivery date
                if order_day.weekday() == 1:  # Tuesday
                    delivery_date = order_day + timedelta(days=1)  # Wednesday
                elif order_day.weekday() == 3:  # Thursday  
                    delivery_date = order_day + timedelta(days=1)  # Friday
                else:
                    return None  # Invalid order day
                
                # Create order
                order = Order.objects.create(
                    restaurant=customer,
                    order_date=order_day,
                    delivery_date=delivery_date,
                    status=random.choice(['delivered', 'delivered', 'delivered', 'confirmed']),  # Mostly delivered
                    original_message=f"Realistic order based on WhatsApp patterns for {customer.get_full_name()}",
                    parsed_by_ai=True
                )
                
                # Add order items based on pattern
                typical_products = pattern.get('typical_products', [])
                avg_items = pattern.get('avg_items', 5)
                
                # Select random subset of typical products
                num_items = random.randint(max(1, avg_items - 3), avg_items + 2)
                selected_products = random.sample(typical_products, min(num_items, len(typical_products)))
                
                total_amount = Decimal('0.00')
                
                for product_spec in selected_products:
                    # Find the product
                    product = Product.objects.filter(name=product_spec['name']).first()
                    if not product:
                        continue
                    
                    # Generate realistic quantity
                    qty_range = product_spec.get('qty_range', (1, 3))
                    quantity = Decimal(str(random.randint(qty_range[0], qty_range[1])))
                    
                    # Get customer-specific price
                    price_item = CustomerPriceListItem.objects.filter(
                        price_list__customer=customer,
                        product=product,
                        price_list__status='active'
                    ).first()
                    
                    if price_item:
                        unit_price = price_item.customer_price_incl_vat
                    else:
                        unit_price = product.price
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        unit=product_spec.get('unit', product.unit),
                        price=unit_price,
                        original_text=f"{quantity} x {product.name}",
                        confidence_score=0.95,
                        notes=f"Based on typical {customer.get_full_name()} order pattern"
                    )
                    
                    total_amount += quantity * unit_price
                
                # Update order totals
                order.subtotal = total_amount
                order.total_amount = total_amount
                order.save()
                
                return order
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating order for {customer.get_full_name()}: {e}'))
            return None
