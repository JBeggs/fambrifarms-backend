"""
Django management command to verify stock take completion

Usage:
    python manage.py verify_stock_take
    python manage.py verify_stock_take --date 2024-12-08
"""

from django.core.management.base import BaseCommand
from inventory.models import StockMovement
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

class Command(BaseCommand):
    help = 'Verify stock take completion and show detailed information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to check (YYYY-MM-DD), defaults to today',
        )

    def handle(self, *args, **options):
        if options['date']:
            try:
                check_date = timezone.datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format. Use YYYY-MM-DD"))
                return
        else:
            check_date = timezone.now().date()
        
        date_str = check_date.strftime('%Y%m%d')
        prefix = f'STOCK-TAKE-{date_str}'
        
        movements = StockMovement.objects.filter(
            reference_number__startswith=prefix
        )
        
        count = movements.count()
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Stock Take Verification for {check_date}")
        self.stdout.write(f"{'='*60}\n")
        
        if count == 0:
            self.stdout.write(self.style.WARNING(f"❌ No stock take movements found for {check_date}"))
            self.stdout.write(f"   Reference prefix: {prefix}")
            
            # Check nearby dates
            yesterday = check_date - timedelta(days=1)
            day_before = check_date - timedelta(days=2)
            
            yesterday_prefix = f'STOCK-TAKE-{yesterday.strftime("%Y%m%d")}'
            day_before_prefix = f'STOCK-TAKE-{day_before.strftime("%Y%m%d")}'
            
            yesterday_count = StockMovement.objects.filter(
                reference_number__startswith=yesterday_prefix
            ).count()
            
            day_before_count = StockMovement.objects.filter(
                reference_number__startswith=day_before_prefix
            ).count()
            
            if yesterday_count > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Found {yesterday_count} movements for yesterday ({yesterday})"))
            if day_before_count > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Found {day_before_count} movements for day before ({day_before})"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Found {count} stock take movements"))
            self.stdout.write(f"   Reference prefix: {prefix}\n")
            
            # Movement types breakdown
            movement_types = movements.values('movement_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            self.stdout.write("Movement Types:")
            for mt in movement_types:
                self.stdout.write(f"   - {mt['movement_type']}: {mt['count']} movements")
            
            # Products affected
            products_count = movements.values('product').distinct().count()
            self.stdout.write(f"\nProducts Affected: {products_count}")
            
            # Time range
            first_movement = movements.order_by('timestamp').first()
            last_movement = movements.order_by('-timestamp').first()
            
            if first_movement and last_movement:
                self.stdout.write(f"First Movement: {first_movement.timestamp}")
                self.stdout.write(f"Last Movement: {last_movement.timestamp}")
            
            # Sample movements
            self.stdout.write("\nSample Movements (first 5):")
            for movement in movements[:5]:
                self.stdout.write(
                    f"   - {movement.product.name} | "
                    f"{movement.quantity} {movement.product.unit} | "
                    f"{movement.movement_type} | "
                    f"{movement.timestamp}"
                )
        
        self.stdout.write(f"\n{'='*60}\n")

