"""
Management command to fix wastage reference numbers from old ADJ- format to STOCK-TAKE- format.

Usage:
    python manage.py fix_wastage_reference_numbers --dry-run  # Preview changes
    python manage.py fix_wastage_reference_numbers             # Apply changes
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from inventory.models import StockMovement


class Command(BaseCommand):
    help = 'Fix wastage reference numbers from ADJ- format to STOCK-TAKE- format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN MODE - No changes will be made ===\n'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  WARNING: This will update wastage records in the database!'))
            confirm = input('Type "yes" to continue: ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return
        
        # Find all wastage movements with ADJ- reference_number that contain stock_take_wastage in notes
        wastage_movements = StockMovement.objects.filter(
            movement_type='finished_waste',
            reference_number__startswith='ADJ-',
            notes__icontains='stock_take_wastage'
        ).order_by('timestamp')
        
        self.stdout.write(f'Found {wastage_movements.count()} wastage records to update\n')
        
        updated_count = 0
        
        with transaction.atomic():
            for movement in wastage_movements:
                # Extract date from timestamp
                date_str = movement.timestamp.strftime('%Y%m%d')
                new_reference_number = f'STOCK-TAKE-{date_str}'
                
                # Extract just the reason from notes (remove "Reason: stock_take_wastage. Stock take wastage: " prefix)
                notes = movement.notes or ''
                if 'Stock take wastage: ' in notes:
                    # Extract the reason part after "Stock take wastage: "
                    reason = notes.split('Stock take wastage: ')[-1].strip()
                else:
                    reason = notes.strip()
                
                self.stdout.write(
                    f'Product: {movement.product.name if movement.product else "Unknown"} '
                    f'(ID: {movement.product_id if movement.product else "N/A"})\n'
                    f'  Old ref: {movement.reference_number}\n'
                    f'  New ref: {new_reference_number}\n'
                    f'  Old notes: {movement.notes}\n'
                    f'  New notes: {reason}\n'
                )
                
                if not dry_run:
                    movement.reference_number = new_reference_number
                    movement.notes = reason  # Store just the reason, no prefix
                    movement.save()
                    updated_count += 1
                else:
                    updated_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== SUMMARY ==='))
        self.stdout.write(f"Wastage records to update: {updated_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN - No changes were made ==='))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {updated_count} wastage records!'))
