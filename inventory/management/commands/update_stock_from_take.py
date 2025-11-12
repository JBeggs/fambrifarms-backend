"""
Management command to update stock levels from stock take data.

Usage:
    python manage.py update_stock_from_take --dry-run  # Preview changes
    python manage.py update_stock_from_take             # Apply changes
    python manage.py update_stock_from_take --confirm    # Skip confirmation prompt
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from inventory.models import FinishedInventory, StockMovement
from products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Update stock levels from stock take data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt (use with caution!)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_confirm = options['confirm']
        
        # Stock take data
        stock_take_data = [
            {'product': 'Avocado (Semi-Ripe)', 'stock_kg': '3.5', 'packaged': '-', 'unit': 'kg', 'comment': '2 box', 'wastage': '-', 'reason': '-'},
            {'product': 'Avocado (Soft)', 'stock_kg': '4.4', 'packaged': '-', 'unit': 'kg', 'comment': '5 box', 'wastage': '-', 'reason': '-'},
            {'product': 'Baby Corn (100g)', 'stock_kg': '1.7', 'packaged': '17.00', 'unit': 'punnet', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Baby Marrow', 'stock_kg': '4', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Baby Marrow (400g)', 'stock_kg': '8.8', 'packaged': '21.00', 'unit': 'punnet', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Bananas', 'stock_kg': '16', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Beetroot', 'stock_kg': '34', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Brinjals', 'stock_kg': '7', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Butternut', 'stock_kg': '43.9', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Button Mushrooms (200g)', 'stock_kg': '0.2', 'packaged': '1.00', 'unit': 'punnet', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Carrots', 'stock_kg': '5.2', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Cauliflower (head)', 'stock_kg': '16.7', 'packaged': '23.00', 'unit': 'head', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Celery', 'stock_kg': '5.5', 'packaged': '7.00', 'unit': 'bunch', 'comment': '-', 'wastage': '0.01', 'reason': 'Spoilage'},
            {'product': 'Cocktail Tomatoes (200g)', 'stock_kg': '2.4', 'packaged': '25.00', 'unit': 'punnet', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Crushed Garlic', 'stock_kg': '1', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Cucumber', 'stock_kg': '149.8', 'packaged': '39.00', 'unit': 'each', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Garlic Cloves', 'stock_kg': '7', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Grapefruit', 'stock_kg': '21.4', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Grapefruit', 'stock_kg': '-', 'packaged': '0.00', 'unit': 'each', 'comment': '-', 'wastage': '1.00', 'reason': 'Spoiled'},
            {'product': 'Green Apples', 'stock_kg': '4', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Green Chillies', 'stock_kg': '10.9', 'packaged': '-', 'unit': 'kg', 'comment': '4 bags', 'wastage': '-', 'reason': '-'},
            {'product': 'Green Grapes (500g)', 'stock_kg': '4.5', 'packaged': '9.00', 'unit': 'punnet', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Green Peppers', 'stock_kg': '0.8', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'green pumpkin', 'stock_kg': '7.5', 'packaged': '5.00', 'unit': 'head', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Iceberg Lettuce', 'stock_kg': '5.2', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '1.60', 'reason': 'Spoiled'},
            {'product': 'Leeks', 'stock_kg': '7.8', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Lemons', 'stock_kg': '78.3', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Lime', 'stock_kg': '4.2', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '0.90', 'reason': 'Spoilage'},
            {'product': 'Naartjies', 'stock_kg': '4.8', 'packaged': '-', 'unit': 'kg', 'comment': '3 boxes', 'wastage': '-', 'reason': '-'},
            {'product': 'Orange Sweet Potatoe', 'stock_kg': '9', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Papaya (head)', 'stock_kg': '5.3', 'packaged': '8.00', 'unit': 'head', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Parsley', 'stock_kg': '0', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '34.60', 'reason': 'Rotten Yellowing'},
            {'product': 'Pineapple', 'stock_kg': '13', 'packaged': '-', 'unit': 'kg', 'comment': '14', 'wastage': '-', 'reason': '-'},
            {'product': 'Potatoes', 'stock_kg': '20.4', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Red Apples', 'stock_kg': '7', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Red Cabbage', 'stock_kg': '10', 'packaged': '6.00', 'unit': 'head', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Red Chillies', 'stock_kg': '7', 'packaged': '-', 'unit': 'kg', 'comment': '2 boxes', 'wastage': '2.00', 'reason': 'Spoiled'},
            {'product': 'Red Grapes (500g)', 'stock_kg': '4.5', 'packaged': '9.00', 'unit': 'punnet', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Spanspek', 'stock_kg': '4', 'packaged': '-', 'unit': 'kg', 'comment': '3 head', 'wastage': '-', 'reason': '-'},
            {'product': 'Spinach', 'stock_kg': '18', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '16.00', 'reason': 'Yellowing'},
            {'product': 'Spring Onions', 'stock_kg': '1.8', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '0.02', 'reason': 'Spoilage'},
            {'product': 'Sweet Corn', 'stock_kg': '5', 'packaged': '-', 'unit': 'kg', 'comment': '7 punnets', 'wastage': '-', 'reason': '-'},
            {'product': 'Sweet Corn (700g)', 'stock_kg': '5', 'packaged': '7.00', 'unit': 'punnet', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Sweet Melon', 'stock_kg': '11.4', 'packaged': '-', 'unit': 'kg', 'comment': '6 heads', 'wastage': '-', 'reason': '-'},
            {'product': 'Sweet Potatoes', 'stock_kg': '23', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Tomatoes', 'stock_kg': '22.2', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'Tomatoes Semi Ripe', 'stock_kg': '13', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
            {'product': 'White Onions', 'stock_kg': '18.1', 'packaged': '-', 'unit': 'kg', 'comment': '-', 'wastage': '-', 'reason': '-'},
        ]
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN MODE - No changes will be made ===\n'))
        else:
            if not skip_confirm:
                self.stdout.write(self.style.WARNING('\n⚠️  WARNING: This will update stock levels in the database!'))
                confirm = input('Type "yes" to continue: ')
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.ERROR('Aborted.'))
                    return
        
        # Get or create a system user for stock movements
        try:
            system_user = User.objects.filter(is_superuser=True).first()
            if not system_user:
                system_user = User.objects.first()
        except:
            self.stdout.write(self.style.ERROR('Error: No user found. Stock movements need a user.'))
            return
        
        processed = []
        not_found = []
        errors = []
        processed_product_ids = set()  # Track which products were in stock take
        zeroed_count = 0  # Count of products set to 0
        
        with transaction.atomic():
            for row in stock_take_data:
                product_name = row['product'].strip()
                unit = row['unit'].strip().lower()
                stock_kg_str = row['stock_kg'].strip()
                comment = row['comment'].strip()
                wastage_str = row['wastage'].strip()
                reason = row['reason'].strip()
                
                # Check if there's wastage to record (even if stock is empty)
                has_wastage = wastage_str and wastage_str != '-' and wastage_str.strip()
                
                # Determine stock value: if unit is NOT kg, use comment field; otherwise use stock_kg
                if unit != 'kg':
                    # When unit is not kg, comment field IS the stock count (kg) value
                    if comment and comment != '-':
                        stock_value_str = comment  # Comment field contains the kg value directly
                    else:
                        stock_value_str = stock_kg_str  # Fallback to stock_kg if comment is empty
                else:
                    # Use stock_kg column when unit IS kg
                    stock_value_str = stock_kg_str
                
                # Skip if stock value is empty AND there's no wastage to record
                if (not stock_value_str or stock_value_str == '-') and not has_wastage:
                    continue
                
                # If stock is empty but there's wastage, set stock to 0
                if not stock_value_str or stock_value_str == '-':
                    stock_value_str = '0'
                
                # Parse stock value
                try:
                    # Replace comma with dot for decimal parsing
                    stock_value_str = stock_value_str.replace(',', '.')
                    stock_value = Decimal(stock_value_str)
                except (InvalidOperation, ValueError) as e:
                    # If there's wastage, still try to process it with stock = 0
                    if has_wastage:
                        stock_value = Decimal('0.00')
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️  Invalid stock value '{stock_value_str}' for {product_name}, "
                                f"but wastage found. Setting stock to 0 and recording wastage."
                            )
                        )
                    else:
                        errors.append(f"{product_name}: Invalid stock value '{stock_value_str}' - {e}")
                        continue
                
                # Find product by name AND unit (case-insensitive, flexible matching)
                product = None
                
                # First try: exact name match with unit match
                product = Product.objects.filter(
                    name__iexact=product_name,
                    unit__iexact=unit
                ).first()
                
                # Second try: exact name match (ignore unit)
                if not product:
                    product = Product.objects.filter(name__iexact=product_name).first()
                
                # Third try: partial name match with unit match
                if not product:
                    product = Product.objects.filter(
                        name__icontains=product_name,
                        unit__iexact=unit
                    ).first()
                
                # Fourth try: partial name match (ignore unit)
                if not product:
                    product = Product.objects.filter(name__icontains=product_name).first()
                
                # Last try: reverse partial match (product name contains search term)
                if not product:
                    # Split product name and try matching parts
                    name_parts = product_name.lower().split()
                    for part in name_parts:
                        if len(part) > 3:  # Only try meaningful parts
                            product = Product.objects.filter(name__icontains=part).first()
                            if product:
                                break
                
                if not product:
                    not_found.append(f"{product_name} ({unit})")
                    continue
                
                # Check if product unit matches - if not, log warning
                if product.unit.lower() != unit.lower():
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Unit mismatch for {product.name}: "
                            f"Database has '{product.unit}', stock take has '{unit}'. "
                            f"Updating product unit to '{unit}'."
                        )
                    )
                    if not dry_run:
                        product.unit = unit
                        product.save()
                
                # Get or create FinishedInventory
                inventory, created = FinishedInventory.objects.get_or_create(
                    product=product,
                    defaults={
                        'available_quantity': Decimal('0.00'),
                        'reserved_quantity': Decimal('0.00'),
                        'minimum_level': Decimal('10.00'),
                        'reorder_level': Decimal('20.00'),
                        'average_cost': product.price or Decimal('0.00'),
                    }
                )
                
                old_stock = inventory.available_quantity or Decimal('0.00')
                
                # Parse wastage (for audit trail only - stock_value is already the final usable count)
                wastage_value = Decimal('0.00')
                if wastage_str and wastage_str != '-':
                    try:
                        wastage_str_clean = wastage_str.replace(',', '.')
                        wastage_value = Decimal(wastage_str_clean)
                    except (InvalidOperation, ValueError) as e:
                        errors.append(f"{product_name}: Invalid wastage value '{wastage_str}' - {e}")
                
                # Track this product as processed (so it won't be set to 0 later)
                processed_product_ids.add(product.id)
                
                # Set stock to counted value (this is the final usable stock after wastage)
                # Note: This sets available_quantity directly - reserved_quantity is preserved
                if not dry_run:
                    inventory.available_quantity = stock_value
                    inventory.save()
                    
                    # Sync Product stock_level
                    product.stock_level = stock_value
                    product.save()
                    
                    # Create stock movement for setting stock
                    StockMovement.objects.create(
                        movement_type='finished_set',
                        reference_number=f"STOCK-TAKE-{timezone.now().strftime('%Y%m%d')}",
                        product=product,
                        quantity=stock_value,
                        user=system_user,
                        notes=f"Stock take: Set to {stock_value} kg (unit: {unit}, comment: {comment})"
                    )
                    
                    # Record wastage separately for audit trail (if any)
                    if wastage_value > 0:
                        StockMovement.objects.create(
                            movement_type='finished_waste',
                            reference_number=f"STOCK-TAKE-{timezone.now().strftime('%Y%m%d')}",
                            product=product,
                            quantity=wastage_value,
                            user=system_user,
                            notes=f"Stock take wastage: {reason or 'No reason provided'}"
                        )
                
                processed.append({
                    'product': product.name,
                    'old': old_stock,
                    'new': stock_value,
                    'unit': unit,
                    'wastage': wastage_value,
                })
                
                wastage_info = f" (wastage: {wastage_value} kg)" if wastage_value > 0 else ""
                self.stdout.write(
                    f"✓ {product.name} (ID: {product.id}): "
                    f"{old_stock} kg → {stock_value} kg{wastage_info}"
                )
            
            # Set all other products (not in stock take) to 0
            self.stdout.write(self.style.WARNING('\n=== Setting other products to 0 ==='))
            self.stdout.write(f'Products in stock take (will NOT be zeroed): {len(processed_product_ids)}')
            all_products = Product.objects.filter(is_active=True)
            
            for product in all_products:
                if product.id not in processed_product_ids:
                    # Get or create FinishedInventory
                    inventory, created = FinishedInventory.objects.get_or_create(
                        product=product,
                        defaults={
                            'available_quantity': Decimal('0.00'),
                            'reserved_quantity': Decimal('0.00'),
                            'minimum_level': Decimal('10.00'),
                            'reorder_level': Decimal('20.00'),
                            'average_cost': product.price or Decimal('0.00'),
                        }
                    )
                    
                    old_stock = inventory.available_quantity or Decimal('0.00')
                    
                    # Only update if stock is not already 0
                    if old_stock > 0:
                        if not dry_run:
                            inventory.available_quantity = Decimal('0.00')
                            inventory.save()
                            
                            # Sync Product stock_level
                            product.stock_level = Decimal('0.00')
                            product.save()
                            
                            # Create stock movement
                            StockMovement.objects.create(
                                movement_type='finished_set',
                                reference_number=f"STOCK-TAKE-{timezone.now().strftime('%Y%m%d')}",
                                product=product,
                                quantity=Decimal('0.00'),
                                user=system_user,
                                notes=f"Stock take: Set to 0 kg (not in stock take list)"
                            )
                        
                        self.stdout.write(
                            f"  → {product.name} (ID: {product.id}): {old_stock} kg → 0 kg"
                        )
                        zeroed_count += 1
            
            if zeroed_count == 0:
                self.stdout.write("  (No products needed to be zeroed)")
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== SUMMARY ==='))
        self.stdout.write(f"Stock take items processed: {len(processed)} products")
        self.stdout.write(f"Other products set to 0: {zeroed_count} products")
        self.stdout.write(f"Not found: {len(not_found)} products")
        self.stdout.write(f"Errors: {len(errors)}")
        
        if not_found:
            self.stdout.write(self.style.WARNING('\n⚠️  Products not found:'))
            for name in not_found:
                self.stdout.write(f"  - {name}")
        
        if errors:
            self.stdout.write(self.style.ERROR('\n❌ Errors:'))
            for error in errors:
                self.stdout.write(f"  - {error}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN - No changes were made ==='))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Stock levels updated successfully!'))

