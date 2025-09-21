from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import FinishedInventory
from products.models import Product


class Command(BaseCommand):
    help = 'Sync Product.stock_level with FinishedInventory.available_quantity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all FinishedInventory records
        finished_inventories = FinishedInventory.objects.select_related('product').all()
        
        updated_count = 0
        created_count = 0
        
        with transaction.atomic():
            for inventory in finished_inventories:
                product = inventory.product
                old_stock = product.stock_level
                new_stock = inventory.available_quantity
                
                if old_stock != new_stock:
                    self.stdout.write(
                        f'Product {product.name} (ID: {product.id}): '
                        f'{old_stock} -> {new_stock}'
                    )
                    
                    if not dry_run:
                        product.stock_level = new_stock
                        product.save()
                    
                    updated_count += 1
            
            # Also check for Products without FinishedInventory records
            products_without_inventory = Product.objects.filter(inventory__isnull=True)
            
            for product in products_without_inventory:
                self.stdout.write(
                    f'Creating FinishedInventory for {product.name} (ID: {product.id}) '
                    f'with stock level: {product.stock_level}'
                )
                
                if not dry_run:
                    FinishedInventory.objects.create(
                        product=product,
                        available_quantity=product.stock_level or 0,
                        reserved_quantity=0,
                        minimum_level=10,
                        reorder_level=20,
                        average_cost=product.price or 0,
                    )
                
                created_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN: Would update {updated_count} products and create {created_count} inventory records'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {updated_count} products and created {created_count} inventory records'
                )
            )
