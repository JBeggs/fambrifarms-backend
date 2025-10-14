#!/usr/bin/env python3
"""
Django management command to set all product prices to 100

Usage:
    python manage.py set_all_products_price_100 [--dry-run] [--backup]

Options:
    --dry-run    Show what would be changed without making changes
    --backup     Create a backup CSV of current prices before changing
"""

import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product


class Command(BaseCommand):
    help = 'Set all product prices to 100'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create a backup CSV of current prices before changing',
        )
        parser.add_argument(
            '--price',
            type=float,
            default=100.0,
            help='Price to set for all products (default: 100.0)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        backup = options['backup']
        new_price = options['price']
        
        self.stdout.write(f"{'🔍 DRY RUN: ' if dry_run else ''}Setting all product prices to R{new_price}")
        
        # Get all products
        products = Product.objects.all().order_by('id')
        total_products = products.count()
        
        if total_products == 0:
            self.stdout.write(self.style.WARNING('No products found in database'))
            return
        
        self.stdout.write(f"Found {total_products} products")
        
        # Create backup if requested
        if backup and not dry_run:
            backup_filename = f"product_prices_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            backup_path = os.path.join('backups', backup_filename)
            
            # Create backups directory if it doesn't exist
            os.makedirs('backups', exist_ok=True)
            
            with open(backup_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['id', 'name', 'department', 'unit', 'old_price'])
                
                for product in products:
                    writer.writerow([
                        product.id,
                        product.name,
                        product.department.name if product.department else '',
                        product.unit,
                        str(product.price),
                    ])
            
            self.stdout.write(self.style.SUCCESS(f'💾 Backup created at: {backup_path}'))
        
        # Show sample of what will change
        self.stdout.write("\n📋 Sample of changes:")
        sample_products = products[:5]
        for product in sample_products:
            old_price = product.price
            self.stdout.write(
                f"  • {product.name} ({product.unit}): "
                f"R{old_price} → R{new_price}"
            )
        
        if total_products > 5:
            self.stdout.write(f"  ... and {total_products - 5} more products")
        
        # Confirm before proceeding (unless dry run)
        if not dry_run:
            self.stdout.write(f"\n⚠️  This will update {total_products} products!")
            confirm = input("Type 'yes' to proceed: ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
                return
        
        # Update products
        if not dry_run:
            self.stdout.write("\n🔄 Updating products...")
            
            with transaction.atomic():
                updated_count = 0
                for product in products:
                    old_price = product.price
                    
                    product.price = new_price
                    product.save()
                    
                    updated_count += 1
                    
                    # Show progress every 100 products
                    if updated_count % 100 == 0:
                        self.stdout.write(f"  ✅ Updated {updated_count}/{total_products} products...")
                
                self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully updated {updated_count} products!'))
                self.stdout.write(f"   • Price set to: R{new_price}")
        else:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN COMPLETE - No changes made'))
        
        # Show summary statistics
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   • Total products: {total_products}")
        if not dry_run:
            self.stdout.write(f"   • Updated: {total_products}")
            self.stdout.write(f"   • New price: R{new_price}")
            if backup:
                self.stdout.write(f"   • Backup: {backup_path}")
        else:
            self.stdout.write(f"   • Would update: {total_products}")
            self.stdout.write(f"   • Target price: R{new_price}")
        
        self.stdout.write(f"\n✅ Command completed!")

        # Show rollback instructions
        if not dry_run and backup:
            self.stdout.write(f"\n🔄 To rollback changes, use:")
            self.stdout.write(f"   python manage.py restore_product_prices_from_backup {backup_path}")
