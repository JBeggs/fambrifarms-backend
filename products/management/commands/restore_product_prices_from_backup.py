#!/usr/bin/env python3
"""
Django management command to restore product prices from a CSV backup

Usage:
    python manage.py restore_product_prices_from_backup <backup_file.csv> [--dry-run]

Options:
    --dry-run    Show what would be changed without making changes
"""

import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from products.models import Product


class Command(BaseCommand):
    help = 'Restore product prices from a CSV backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Path to the CSV backup file to restore from',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        dry_run = options['dry_run']
        
        self.stdout.write(f"{'🔍 DRY RUN: ' if dry_run else ''}Restoring product prices from backup")
        
        # Check if backup file exists
        if not os.path.exists(backup_file):
            raise CommandError(f'Backup file not found: {backup_file}')
        
        self.stdout.write(f"📁 Reading backup file: {backup_file}")
        
        # Read backup file
        restore_data = []
        try:
            with open(backup_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    restore_data.append({
                        'id': int(row['id']),
                        'name': row['name'],
                        'department': row['department'],
                        'unit': row['unit'],
                        'old_price': float(row['old_price']),
                    })
        except Exception as e:
            raise CommandError(f'Error reading backup file: {e}')
        
        if not restore_data:
            raise CommandError('No data found in backup file')
        
        self.stdout.write(f"📊 Found {len(restore_data)} products in backup")
        
        # Show sample of what will be restored
        self.stdout.write("\n📋 Sample of changes:")
        sample_data = restore_data[:5]
        
        for data in sample_data:
            try:
                product = Product.objects.get(id=data['id'])
                current_price = product.price
                restore_price = data['old_price']
                
                self.stdout.write(
                    f"  • {data['name']} ({data['unit']}): "
                    f"R{current_price} → R{restore_price}"
                )
            except Product.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠️  Product ID {data['id']} ({data['name']}) not found - will skip"
                    )
                )
        
        if len(restore_data) > 5:
            self.stdout.write(f"  ... and {len(restore_data) - 5} more products")
        
        # Confirm before proceeding (unless dry run)
        if not dry_run:
            self.stdout.write(f"\n⚠️  This will restore {len(restore_data)} products!")
            confirm = input("Type 'yes' to proceed: ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
                return
        
        # Restore products
        if not dry_run:
            self.stdout.write("\n🔄 Restoring products...")
            
            with transaction.atomic():
                updated_count = 0
                skipped_count = 0
                
                for data in restore_data:
                    try:
                        product = Product.objects.get(id=data['id'])
                        
                        # Verify product matches backup data
                        if product.name != data['name']:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  ⚠️  Product ID {data['id']} name mismatch: "
                                    f"current='{product.name}' vs backup='{data['name']}' - skipping"
                                )
                            )
                            skipped_count += 1
                            continue
                        
                        # Restore price  
                        product.price = data['old_price']
                        product.save()
                        
                        updated_count += 1
                        
                        # Show progress every 100 products
                        if updated_count % 100 == 0:
                            self.stdout.write(f"  ✅ Restored {updated_count}/{len(restore_data)} products...")
                    
                    except Product.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️  Product ID {data['id']} ({data['name']}) not found - skipping"
                            )
                        )
                        skipped_count += 1
                        continue
                
                self.stdout.write(self.style.SUCCESS(f'\n🎉 Restore completed!'))
                self.stdout.write(f"   • Restored: {updated_count} products")
                if skipped_count > 0:
                    self.stdout.write(self.style.WARNING(f"   • Skipped: {skipped_count} products"))
        else:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN COMPLETE - No changes made'))
            
            # Count what would be processed
            found_count = 0
            missing_count = 0
            for data in restore_data:
                try:
                    Product.objects.get(id=data['id'], name=data['name'])
                    found_count += 1
                except Product.DoesNotExist:
                    missing_count += 1
            
            self.stdout.write(f"   • Would restore: {found_count} products")
            if missing_count > 0:
                self.stdout.write(f"   • Would skip: {missing_count} products (not found)")
        
        self.stdout.write(f"\n✅ Command completed!")
