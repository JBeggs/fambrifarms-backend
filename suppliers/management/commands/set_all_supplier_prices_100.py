from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import datetime
import os
import csv

from suppliers.models import SupplierProduct


class Command(BaseCommand):
    help = 'Sets the supplier price of all supplier products to R100'

    def add_arguments(self, parser):
        parser.add_argument(
            '--price',
            type=Decimal,
            default=Decimal('100.00'),
            help='The new supplier price to set for all supplier products.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without making any database changes.',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create a CSV backup of current supplier prices before making changes.',
        )

    def handle(self, *args, **options):
        new_price = options['price']
        dry_run = options['dry_run']
        create_backup = options['backup']

        self.stdout.write(self.style.SUCCESS(f'🔍 {"DRY RUN: " if dry_run else ""}Setting all supplier prices to R{new_price}'))

        supplier_products = SupplierProduct.objects.select_related('supplier', 'product')
        total_products = supplier_products.count()
        self.stdout.write(f'Found {total_products} supplier products')

        if create_backup and not dry_run:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join('backups', f'supplier_prices_backup_{timestamp}.csv')
            os.makedirs('backups', exist_ok=True)
            
            with open(backup_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    'id', 'supplier_name', 'product_name', 'supplier_product_code', 
                    'old_supplier_price', 'currency', 'is_available'
                ])
                
                for sp in supplier_products:
                    writer.writerow([
                        sp.id,
                        sp.supplier.name,
                        sp.product.name,
                        sp.supplier_product_code,
                        str(sp.supplier_price),
                        sp.currency,
                        sp.is_available,
                    ])
            
            self.stdout.write(self.style.SUCCESS(f'💾 Backup created at: {backup_path}'))
        
        self.stdout.write("\n📋 Sample of changes:")
        sample_products = supplier_products[:5]
        for sp in sample_products:
            old_price = sp.supplier_price
            self.stdout.write(
                f"  • {sp.supplier.name} - {sp.product.name}: "
                f"R{old_price} → R{new_price}"
            )
        
        if total_products > 5:
            self.stdout.write(f"  ... and {total_products - 5} more supplier products")
        
        if not dry_run:
            confirm = input(self.style.WARNING(
                f'\nAre you sure you want to set the supplier price of {total_products} supplier products to R{new_price}? (yes/no): '
            )).lower()
            if confirm != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled.'))
                return

            self.stdout.write("\n🔄 Updating supplier products...")
            
            with transaction.atomic():
                updated_count = 0
                for sp in supplier_products:
                    old_price = sp.supplier_price
                    
                    sp.supplier_price = new_price
                    sp.save()
                    
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        self.stdout.write(f"  ✅ Updated {updated_count}/{total_products} supplier products...")
                
                self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully updated {updated_count} supplier products!'))
                self.stdout.write(f"   • Supplier price set to: R{new_price}")
        else:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN COMPLETE - No changes made'))
        
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   • Total supplier products: {total_products}")
        self.stdout.write(f"   • Would update: {total_products}")
        self.stdout.write(f"   • Target supplier price: R{new_price}")
        if create_backup and not dry_run:
            self.stdout.write(f"   • Backup: {backup_path}")

        self.stdout.write(self.style.SUCCESS('\n✅ Command completed!'))
