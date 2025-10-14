from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import csv
import os

from suppliers.models import SupplierProduct


class Command(BaseCommand):
    help = 'Restores supplier prices from a CSV backup file.'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='The path to the CSV backup file.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without making any database changes.',
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS(f'🔍 {"DRY RUN: " if dry_run else ""}Restoring supplier prices from {backup_file}'))

        if not os.path.exists(backup_file):
            self.stdout.write(self.style.ERROR(f'❌ Backup file not found: {backup_file}'))
            return

        # Read the backup file
        supplier_products_data = []
        try:
            with open(backup_file, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    supplier_products_data.append({
                        'id': int(row['id']),
                        'supplier_name': row['supplier_name'],
                        'product_name': row['product_name'],
                        'supplier_product_code': row['supplier_product_code'],
                        'old_supplier_price': Decimal(row['old_supplier_price']),
                        'currency': row['currency'],
                        'is_available': row['is_available'].lower() == 'true',
                    })
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error reading backup file: {e}'))
            return

        self.stdout.write(f'Found {len(supplier_products_data)} supplier products in backup')

        # Show sample of what will be restored
        self.stdout.write("\n📋 Sample of restorations:")
        sample_data = supplier_products_data[:5]
        for data in sample_data:
            self.stdout.write(
                f"  • {data['supplier_name']} - {data['product_name']}: "
                f"Restore to R{data['old_supplier_price']}"
            )

        if len(supplier_products_data) > 5:
            self.stdout.write(f"  ... and {len(supplier_products_data) - 5} more supplier products")

        if not dry_run:
            confirm = input(self.style.WARNING(
                f'\nAre you sure you want to restore {len(supplier_products_data)} supplier product prices? (yes/no): '
            )).lower()
            if confirm != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled.'))
                return

            self.stdout.write("\n🔄 Restoring supplier prices...")

            with transaction.atomic():
                updated_count = 0
                not_found_count = 0

                for data in supplier_products_data:
                    try:
                        sp = SupplierProduct.objects.get(id=data['id'])
                        current_price = sp.supplier_price
                        sp.supplier_price = data['old_supplier_price']
                        sp.save()

                        updated_count += 1

                        if updated_count % 100 == 0:
                            self.stdout.write(f"  ✅ Restored {updated_count}/{len(supplier_products_data)} supplier prices...")

                    except SupplierProduct.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠️  Supplier product not found: ID {data['id']} - {data['supplier_name']} - {data['product_name']}"
                        ))
                        not_found_count += 1

                self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully restored {updated_count} supplier product prices!'))
                if not_found_count > 0:
                    self.stdout.write(self.style.WARNING(f'⚠️  {not_found_count} supplier products not found'))
        else:
            self.stdout.write(self.style.WARNING('\n🔍 DRY RUN COMPLETE - No changes made'))

        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   • Total in backup: {len(supplier_products_data)}")
        self.stdout.write(f"   • Would restore: {len(supplier_products_data) - (0 if dry_run else not_found_count)}")
        if not dry_run and not_found_count > 0:
            self.stdout.write(f"   • Not found: {not_found_count}")

        self.stdout.write(self.style.SUCCESS('\n✅ Command completed!'))
