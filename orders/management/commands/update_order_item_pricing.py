from django.core.management.base import BaseCommand
from django.db import transaction
from orders.models import Order, OrderItem
from whatsapp.services import get_customer_specific_price
from decimal import Decimal


class Command(BaseCommand):
    help = 'Update existing order items to use current pricing logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--order-id',
            type=int,
            help='Update only a specific order ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        order_id = options.get('order_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get order items to update
        if order_id:
            order_items = OrderItem.objects.filter(order_id=order_id).select_related('order', 'order__restaurant', 'product')
            self.stdout.write(f'Updating order items for order ID {order_id}')
        else:
            order_items = OrderItem.objects.all().select_related('order', 'order__restaurant', 'product')
            self.stdout.write(f'Updating all order items ({order_items.count()} items)')
        
        updated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for item in order_items:
                try:
                    if not item.order.restaurant:
                        self.stdout.write(f'⚠️  Skipping item {item.id}: No customer assigned')
                        continue
                    
                    # Get current pricing
                    current_price = get_customer_specific_price(item.product, item.order.restaurant)
                    old_price = item.price
                    old_total = item.total_price
                    
                    # Calculate new total
                    new_total = item.quantity * current_price
                    
                    if old_price != current_price:
                        self.stdout.write(
                            f'📦 {item.product.name} (Order {item.order.id}): '
                            f'{old_price} -> {current_price} '
                            f'(Total: {old_total} -> {new_total})'
                        )
                        
                        if not dry_run:
                            item.price = current_price
                            item.total_price = new_total
                            item.save()
                        
                        updated_count += 1
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'❌ Error updating item {item.id}: {e}')
                    )
        
        # Update order totals
        if not dry_run and updated_count > 0:
            self.stdout.write('🔄 Updating order totals...')
            
            if order_id:
                orders_to_update = Order.objects.filter(id=order_id)
            else:
                orders_to_update = Order.objects.filter(items__in=order_items).distinct()
            
            for order in orders_to_update:
                order.subtotal = sum(item.total_price for item in order.items.all())
                order.total_amount = order.subtotal
                order.save()
                self.stdout.write(f'📊 Updated order {order.id} total: {order.total_amount}')
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'✅ DRY RUN COMPLETE: Would update {updated_count} items')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ UPDATED {updated_count} order items with current pricing')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠️  {error_count} items had errors')
            )
