from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product
from inventory.models import FinishedInventory


class Command(BaseCommand):
    help = 'Clear all product stock levels (set to 0) - stock should only be updated via WhatsApp messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleared without actually clearing',
        )
        parser.add_argument(
            '--include-inventory',
            action='store_true',
            help='Also clear FinishedInventory available quantities',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        include_inventory = options['include_inventory']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )
        
        # Get products with stock levels > 0
        products_with_stock = Product.objects.filter(stock_level__gt=0)
        products_count = products_with_stock.count()
        
        if products_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No products have stock levels > 0')
            )
            return
        
        self.stdout.write(f'Found {products_count} products with stock levels > 0:')
        
        # Show products that will be affected
        for product in products_with_stock[:10]:  # Show first 10
            self.stdout.write(f'  - {product.name}: {product.stock_level} {product.unit}')
        
        if products_count > 10:
            self.stdout.write(f'  ... and {products_count - 10} more')
        
        if include_inventory:
            inventory_with_stock = FinishedInventory.objects.filter(available_quantity__gt=0)
            inventory_count = inventory_with_stock.count()
            self.stdout.write(f'Found {inventory_count} inventory records with available quantity > 0')
        
        if not dry_run:
            # Confirm before proceeding
            confirm = input('\nAre you sure you want to clear all stock levels? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled')
                return
            
            with transaction.atomic():
                # Clear product stock levels
                products_updated = Product.objects.filter(stock_level__gt=0).update(stock_level=0)
                
                if include_inventory:
                    # Clear inventory available quantities
                    inventory_updated = FinishedInventory.objects.filter(
                        available_quantity__gt=0
                    ).update(available_quantity=0)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Cleared stock levels for {products_updated} products '
                            f'and {inventory_updated} inventory records'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Cleared stock levels for {products_updated} products'
                        )
                    )
            
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  Stock levels should now only be updated through:\n'
                    '   1. WhatsApp stock messages (recommended)\n'
                    '   2. Manual inventory adjustments\n'
                    '   3. Stock level sync commands'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'\nWould clear stock levels for {products_count} products'
                )
            )

from django.db import transaction
from products.models import Product
from inventory.models import FinishedInventory


class Command(BaseCommand):
    help = 'Clear all product stock levels (set to 0) - stock should only be updated via WhatsApp messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleared without actually clearing',
        )
        parser.add_argument(
            '--include-inventory',
            action='store_true',
            help='Also clear FinishedInventory available quantities',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        include_inventory = options['include_inventory']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )
        
        # Get products with stock levels > 0
        products_with_stock = Product.objects.filter(stock_level__gt=0)
        products_count = products_with_stock.count()
        
        if products_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No products have stock levels > 0')
            )
            return
        
        self.stdout.write(f'Found {products_count} products with stock levels > 0:')
        
        # Show products that will be affected
        for product in products_with_stock[:10]:  # Show first 10
            self.stdout.write(f'  - {product.name}: {product.stock_level} {product.unit}')
        
        if products_count > 10:
            self.stdout.write(f'  ... and {products_count - 10} more')
        
        if include_inventory:
            inventory_with_stock = FinishedInventory.objects.filter(available_quantity__gt=0)
            inventory_count = inventory_with_stock.count()
            self.stdout.write(f'Found {inventory_count} inventory records with available quantity > 0')
        
        if not dry_run:
            # Confirm before proceeding
            confirm = input('\nAre you sure you want to clear all stock levels? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Operation cancelled')
                return
            
            with transaction.atomic():
                # Clear product stock levels
                products_updated = Product.objects.filter(stock_level__gt=0).update(stock_level=0)
                
                if include_inventory:
                    # Clear inventory available quantities
                    inventory_updated = FinishedInventory.objects.filter(
                        available_quantity__gt=0
                    ).update(available_quantity=0)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Cleared stock levels for {products_updated} products '
                            f'and {inventory_updated} inventory records'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Cleared stock levels for {products_updated} products'
                        )
                    )
            
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  Stock levels should now only be updated through:\n'
                    '   1. WhatsApp stock messages (recommended)\n'
                    '   2. Manual inventory adjustments\n'
                    '   3. Stock level sync commands'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'\nWould clear stock levels for {products_count} products'
                )
            )
