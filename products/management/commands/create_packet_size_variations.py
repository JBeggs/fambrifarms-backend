from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product, Department
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create packet size variations (50g, 100g, 200g) for products that come in packets'

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
        
        # Products that should have packet size variations
        packet_products_config = [
            {
                'base_name': 'Thyme',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.50'),  # R0.50 per gram
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Basil',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.15'),  # R0.15 per gram (based on existing 900g at R15)
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Parsley',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.027'),  # R0.027 per gram (based on existing 3kg at R8)
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Coriander',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.30'),  # R0.30 per gram
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Mint',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.25'),  # R0.25 per gram
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Rosemary',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.40'),  # R0.40 per gram
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Oregano',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.35'),  # R0.35 per gram
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Sage',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.45'),  # R0.45 per gram
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Micro Herbs',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.50'),  # R0.50 per gram (premium product)
                'sizes': [50, 100, 200],  # gram sizes
            },
            {
                'base_name': 'Edible Flowers',
                'department': 'Herbs & Spices',
                'base_price_per_gram': Decimal('0.70'),  # R0.70 per gram (premium product)
                'sizes': [50, 100, 200],  # gram sizes
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for config in packet_products_config:
                department = Department.objects.get(name=config['department'])
                
                for size in config['sizes']:
                    product_name = f"{config['base_name']} ({size}g packet)"
                    price = config['base_price_per_gram'] * size
                    
                    if dry_run:
                        self.stdout.write(f"Would create: {product_name} - R{price:.2f} (packet)")
                        continue
                    
                    # Check if product already exists
                    existing = Product.objects.filter(name=product_name).first()
                    
                    if existing:
                        # Update existing product
                        existing.price = price
                        existing.unit = 'packet'
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
                            unit='packet',
                            stock_level=Decimal('0.00'),
                            minimum_stock=Decimal('10.00'),  # Higher minimum for small packets
                            is_active=True,
                            needs_setup=False,
                        )
                        created_count += 1
                        self.stdout.write(f"Created: {product_name} - R{price:.2f}")
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Packet size variations created successfully!'
                    f'\n📦 Created: {created_count} new products'
                    f'\n🔄 Updated: {updated_count} existing products'
                    f'\n📊 Total products processed: {created_count + updated_count}'
                )
            )
        else:
            total_would_create = sum(len(config['sizes']) for config in packet_products_config)
            self.stdout.write(
                self.style.WARNING(
                    f'\n📋 DRY RUN SUMMARY:'
                    f'\n📦 Would process: {total_would_create} products'
                    f'\n💡 Run without --dry-run to actually create products'
                )
            )
