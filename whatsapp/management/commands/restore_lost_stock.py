from django.core.management.base import BaseCommand
from products.models import Product
from inventory.models import FinishedInventory, StockMovement
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import datetime

class Command(BaseCommand):
    help = 'Restore stock levels that were accidentally reset during stock processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be restored without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Stock levels that were lost based on the stock movements we found
        lost_stock_items = [
            {'name': 'Green Cabbage', 'quantity': 3.0, 'unit': 'head'},
            {'name': 'Iceberg Lettuce', 'quantity': 12.0, 'unit': 'head'},
            {'name': 'Eggplant', 'quantity': 1.8, 'unit': 'kg'},
            {'name': 'Brown Mushrooms', 'quantity': 3.0, 'unit': 'punnet'},
            # Add more items from the screenshot that should have been processed
            {'name': 'Baby Marrow', 'quantity': 3.0, 'unit': 'kg'},
            {'name': 'Deveined Spinach', 'quantity': 3.0, 'unit': 'kg'},
            {'name': 'Cocktail Tomatoes', 'quantity': 25.0, 'unit': 'punnet'},
            {'name': 'Sweet Corn', 'quantity': 1.0, 'unit': 'punnet'},
            {'name': 'Patty Pan', 'quantity': 10.0, 'unit': 'each'},
            {'name': 'Green Grapes', 'quantity': 3.0, 'unit': 'punnet'},
            {'name': 'Red Grapes', 'quantity': 3.0, 'unit': 'punnet'},
            {'name': 'Red Cabbage', 'quantity': 3.0, 'unit': 'head'},
            {'name': 'Cauliflower', 'quantity': 10.0, 'unit': 'head'},
            {'name': 'Cucumber', 'quantity': 17.0, 'unit': 'each'},
            {'name': 'Sweet Melon', 'quantity': 1.0, 'unit': 'each'},
            {'name': 'Watermelon', 'quantity': 1.0, 'unit': 'each'},
            {'name': 'Pineapple', 'quantity': 20.0, 'unit': 'each'},
            {'name': 'Papaya', 'quantity': 6.0, 'unit': 'punnet'},
            {'name': 'Tomatoes', 'quantity': 10.0, 'unit': 'kg'},
            {'name': 'Rocket', 'quantity': 1.5, 'unit': 'kg'},
            {'name': 'Parsley', 'quantity': 1.5, 'unit': 'kg'},
            {'name': 'Mint', 'quantity': 1.0, 'unit': 'kg'},
        ]
        
        User = get_user_model()
        system_user = User.objects.filter(is_staff=True).first()
        if not system_user:
            system_user = User.objects.first()
        
        restored_count = 0
        not_found_count = 0
        
        self.stdout.write('=== RESTORING LOST STOCK LEVELS ===')
        
        with transaction.atomic():
            for item_data in lost_stock_items:
                product_name = item_data['name']
                quantity = item_data['quantity']
                unit = item_data['unit']
                
                try:
                    # Try to find the product
                    product = None
                    try:
                        product = Product.objects.get(name__iexact=product_name)
                    except Product.DoesNotExist:
                        # Try partial match
                        products = Product.objects.filter(name__icontains=product_name)
                        if products.count() == 1:
                            product = products.first()
                        elif products.count() > 1:
                            # Use first match for now
                            product = products.first()
                            self.stdout.write(
                                self.style.WARNING(f'Multiple matches for "{product_name}": {[p.name for p in products]}. Using: {product.name}')
                            )
                    
                    if not product:
                        self.stdout.write(self.style.ERROR(f'❌ Product not found: {product_name}'))
                        not_found_count += 1
                        continue
                    
                    # Check current stock level
                    current_stock = product.stock_level or 0
                    
                    if current_stock > 0:
                        self.stdout.write(f'⚠️  {product.name} already has stock: {current_stock} {product.unit}. Skipping.')
                        continue
                    
                    if not dry_run:
                        # Update product stock level
                        product.stock_level = quantity
                        product.save()
                        
                        # Get or create FinishedInventory record
                        inventory, created = FinishedInventory.objects.get_or_create(
                            product=product,
                            defaults={
                                'available_quantity': quantity,
                                'reserved_quantity': 0,
                                'minimum_level': product.minimum_stock or 10,
                                'reorder_level': product.minimum_stock or 20,
                                'average_cost': product.price or 0,
                            }
                        )
                        
                        if not created:
                            inventory.available_quantity = quantity
                            inventory.save()
                        
                        # Create stock movement record
                        if system_user:
                            StockMovement.objects.create(
                                movement_type='finished_adjust',
                                reference_number=f'RESTORE-{datetime.now().strftime("%Y%m%d%H%M")}',
                                product=product,
                                quantity=quantity,
                                user=system_user,
                                notes=f'Restored stock that was accidentally reset. Original quantity: {quantity} {unit}'
                            )
                    
                    self.stdout.write(self.style.SUCCESS(f'✅ {"Would restore" if dry_run else "Restored"}: {product.name} = {quantity} {unit}'))
                    restored_count += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error processing {product_name}: {e}'))
                    not_found_count += 1
        
        self.stdout.write(f'\n=== SUMMARY ===')
        self.stdout.write(self.style.SUCCESS(f'✅ {"Would restore" if dry_run else "Restored"}: {restored_count} products'))
        self.stdout.write(self.style.ERROR(f'❌ Not found/errors: {not_found_count} products'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔄 This was a dry run. Run without --dry-run to actually restore the stock.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n🎉 Stock restoration completed!'))
