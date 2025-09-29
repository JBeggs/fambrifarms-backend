from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create bag size variations (1kg-10kg) for products that come in bags'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating products',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No products will be created'))
        
        # Products that should have bag size variations
        bag_products_config = [
            {
                'base_name': 'Red Onions',
                'department': 'Vegetables',
                'base_price_per_kg': Decimal('2.50'),  # Approximate price per kg
                'sizes': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # kg sizes
            },
            {
                'base_name': 'White Onions',
                'department': 'Vegetables', 
                'base_price_per_kg': Decimal('2.20'),  # Approximate price per kg
                'sizes': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # kg sizes
            },
            {
                'base_name': 'Potatoes',
                'department': 'Vegetables',
                'base_price_per_kg': Decimal('4.50'),  # Approximate price per kg
                'sizes': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # kg sizes
            },
            {
                'base_name': 'Carrots',
                'department': 'Vegetables',
                'base_price_per_kg': Decimal('2.20'),  # Approximate price per kg
                'sizes': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],  # kg sizes
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for config in bag_products_config:
                department = Department.objects.get(name=config['department'])
                
                for size in config['sizes']:
                    product_name = f"{config['base_name']} ({size}kg bag)"
                    price = config['base_price_per_kg'] * size
                    
                    if dry_run:
                        self.stdout.write(f"Would create: {product_name} - R{price:.2f} (bag)")
                        continue
                    
                    # Check if product already exists
                    existing = Product.objects.filter(name=product_name).first()
                    
                    if existing:
                        # Update existing product
                        existing.price = price
                        existing.unit = 'bag'
                        existing.department = department
                        existing.is_active = True
                        existing.save()
                        updated_count += 1
                        self.stdout.write(f"Updated: {product_name} - R{price:.2f}")
                    else:
                        # Create new product
                        Product.objects.create(
                            name=product_name,
                            department=department,
                            price=price,
                            unit='bag',
                            stock_level=Decimal('0.00'),
                            minimum_stock=Decimal('5.00'),
                            is_active=True,
                            needs_setup=False,
                        )
                        created_count += 1
                        self.stdout.write(f"Created: {product_name} - R{price:.2f}")
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Bag size variations created successfully!'
                    f'\n📦 Created: {created_count} new products'
                    f'\n🔄 Updated: {updated_count} existing products'
                    f'\n📊 Total products processed: {created_count + updated_count}'
                )
            )
        else:
            total_would_create = sum(len(config['sizes']) for config in bag_products_config)
            self.stdout.write(
                self.style.WARNING(
                    f'\n📋 DRY RUN SUMMARY:'
                    f'\n📦 Would process: {total_would_create} products'
                    f'\n💡 Run without --dry-run to actually create products'
                )
            )
