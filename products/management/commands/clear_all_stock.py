from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Product
from inventory.models import FinishedInventory
from whatsapp.models import StockUpdate


class Command(BaseCommand):
    help = 'Clear all stock data from the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all stock data',
        )
        parser.add_argument(
            '--keep-history',
            action='store_true',
            help='Keep WhatsApp stock update history (only clear current stock)',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will delete ALL stock data. Use --confirm to proceed.'
                )
            )
            return

        with transaction.atomic():
            # Clear product stock levels
            products_updated = Product.objects.update(stock_level=0.00)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated {products_updated} products to zero stock level'
                )
            )

            # Clear finished inventory
            finished_inventory_count = FinishedInventory.objects.count()
            FinishedInventory.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Deleted {finished_inventory_count} finished inventory records'
                )
            )

            # Clear stock updates (unless keeping history)
            if not options['keep_history']:
                stock_updates_count = StockUpdate.objects.count()
                StockUpdate.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Deleted {stock_updates_count} stock update records'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'Kept WhatsApp stock update history as requested'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                'Successfully cleared all stock data!'
            )
        )
