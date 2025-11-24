"""
Management command to update packaging_size field on Product model

Usage:
    python manage.py update_packaging_sizes --dry-run  # Preview changes
    python manage.py update_packaging_sizes  # Apply changes
    python manage.py update_packaging_sizes --from-json packaging_updates.json  # Use pre-extracted data
"""

import json
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product


class Command(BaseCommand):
    help = 'Update packaging_size field on Product model based on product names'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them',
        )
        parser.add_argument(
            '--from-json',
            type=str,
            help='Load updates from JSON file (format: [{"id": 123, "name": "...", "unit": "...", "packaging_size": "100g"}, ...])',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each product',
        )

    def extract_packaging_from_name(self, name):
        """
        Extract packaging size from product name using multiple patterns
        
        Returns:
            String like "100g", "1kg", "500g" or None
        """
        # Pattern 1: Product Name (Size)
        match = re.search(r'\((\d+(?:\.\d+)?)(kg|g|ml|l)', name, re.IGNORECASE)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        
        # Pattern 2: Product Name Size packet/bag/box
        match = re.search(r'(\d+(?:\.\d+)?)(kg|g|ml|l)\s+(?:packet|bag|box|punnet)', name, re.IGNORECASE)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        
        # Pattern 3: Product Name Size (standalone at end)
        match = re.search(r'(\d+(?:\.\d+)?)(kg|g|ml|l)\b', name, re.IGNORECASE)
        if match:
            return f"{match.group(1)}{match.group(2)}"
        
        return None

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        json_file = options.get('from_json')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY-RUN mode. No changes will be saved.'))
        
        updates = []
        
        if json_file:
            # Load updates from JSON file
            try:
                with open(json_file, 'r') as f:
                    updates_data = json.load(f)
                    for item in updates_data:
                        try:
                            product = Product.objects.get(id=item['id'])
                            updates.append({
                                'product': product,
                                'packaging_size': item['packaging_size'],
                                'source': 'json_file'
                            })
                        except Product.DoesNotExist:
                            self.stdout.write(self.style.ERROR(f"Product ID {item['id']} not found: {item.get('name', 'Unknown')}"))
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f"JSON file not found: {json_file}"))
                return
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f"Invalid JSON file: {e}"))
                return
        else:
            # Extract from all products
            discrete_units = ['packet', 'head', 'bag', 'box', 'punnet', 'bunch']
            products = Product.objects.filter(unit__in=discrete_units)
            
            self.stdout.write(f"Analyzing {products.count()} products with discrete units...")
            
            for product in products:
                # Skip if already has packaging_size
                if product.packaging_size:
                    continue
                
                # Try to extract from name
                extracted = self.extract_packaging_from_name(product.name)
                if extracted:
                    updates.append({
                        'product': product,
                        'packaging_size': extracted,
                        'source': 'name_extraction'
                    })
        
        if not updates:
            self.stdout.write(self.style.SUCCESS('No products found that need packaging_size updates.'))
            return
        
        # Display updates
        self.stdout.write(self.style.SUCCESS(f'\nFound {len(updates)} products to update:'))
        for update in updates:
            product = update['product']
            packaging = update['packaging_size']
            source = update['source']
            
            if verbose:
                self.stdout.write(f"  • {product.name} (ID: {product.id}, unit: {product.unit}) → {packaging} [{source}]")
            else:
                self.stdout.write(f"  • {product.name} → {packaging}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY-RUN: Would update {len(updates)} products.'))
            return
        
        # Apply updates
        confirm = input(self.style.WARNING(f'\nUpdate {len(updates)} products? Type "yes" to confirm: '))
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.NOTICE('Operation cancelled.'))
            return
        
        updated_count = 0
        with transaction.atomic():
            for update in updates:
                product = update['product']
                packaging = update['packaging_size']
                
                product.packaging_size = packaging
                product.save(update_fields=['packaging_size'])
                updated_count += 1
                
                if verbose:
                    self.stdout.write(f"  ✓ Updated {product.name} (ID: {product.id}) → {packaging}")
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {updated_count} products!'))
        
        # Show products still missing packaging_size
        missing = Product.objects.filter(
            unit__in=['packet', 'head', 'bag', 'box', 'punnet', 'bunch'],
            packaging_size__isnull=True
        ).exclude(packaging_size='')
        
        if missing.exists():
            self.stdout.write(self.style.WARNING(f'\n{missing.count()} products still missing packaging_size:'))
            for product in missing[:20]:
                self.stdout.write(f"  • {product.name} (ID: {product.id}, unit: {product.unit})")
            if missing.count() > 20:
                self.stdout.write(f"  ... and {missing.count() - 20} more")

