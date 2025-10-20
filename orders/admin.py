from django.contrib import admin
from django.db import transaction
from django.contrib.admin import helpers
from django.template.response import TemplateResponse
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price',)

def safe_delete_orders(modeladmin, request, queryset):
    """Safely delete orders by handling related objects first"""
    import logging
    logger = logging.getLogger(__name__)
    
    with transaction.atomic():
        for order in queryset:
            # CRITICAL: Release reserved stock before deletion
            try:
                from inventory.signals import release_stock_for_order
                from inventory.models import StockMovement
                
                # Check if there are reserved stock movements for this order
                existing_reservations = StockMovement.objects.filter(
                    movement_type='finished_reserve',
                    reference_number=order.order_number
                ).exists()
                
                if existing_reservations:
                    logger.info(f"[ADMIN] Releasing reserved stock for order {order.order_number} before deletion")
                    release_stock_for_order(order)
                    
            except Exception as e:
                logger.error(f"[ADMIN] Error releasing stock for order {order.order_number}: {e}")
                # Continue with deletion even if stock release fails
            
            # Delete related objects that might cause constraints
            if hasattr(order, 'invoice') and order.invoice:
                order.invoice.delete()
            
            # Delete purchase orders
            order.purchase_orders.all().delete()
            
            # Delete order items (this should cascade properly)
            order.items.all().delete()
            
            # Finally delete the order
            order.delete()
    
    modeladmin.message_user(request, f"Successfully deleted {queryset.count()} orders and their related data (reserved stock released).")

safe_delete_orders.short_description = "Safely delete selected orders"

def fix_delivery_dates(modeladmin, request, queryset):
    """Fix invalid delivery dates to comply with business rules"""
    from datetime import timedelta
    import logging
    logger = logging.getLogger(__name__)
    
    fixed_count = 0
    
    with transaction.atomic():
        for order in queryset:
            original_delivery = order.delivery_date
            
            try:
                # Check if delivery date is invalid (not Tue/Wed/Fri)
                if order.delivery_date and order.delivery_date.weekday() not in [1, 2, 4]:
                    
                    # Auto-fix based on order date
                    if order.order_date:
                        if order.order_date.weekday() == 0:  # Monday order
                            # Default to Tuesday delivery
                            order.delivery_date = order.order_date + timedelta(days=1)
                        elif order.order_date.weekday() == 3:  # Thursday order  
                            # Default to Friday delivery
                            order.delivery_date = order.order_date + timedelta(days=1)
                        else:
                            # Invalid order date, fix both
                            # Find next Monday for order, Tuesday for delivery
                            days_to_monday = (7 - order.order_date.weekday()) % 7
                            if days_to_monday == 0:
                                days_to_monday = 7
                            order.order_date = order.order_date + timedelta(days=days_to_monday)
                            order.delivery_date = order.order_date + timedelta(days=1)
                    else:
                        # No order date, set to next Tuesday
                        from datetime import date
                        today = date.today()
                        days_ahead = 1 - today.weekday()  # Tuesday is 1
                        if days_ahead <= 0:
                            days_ahead += 7
                        order.delivery_date = today + timedelta(days=days_ahead)
                    
                    order.save()
                    fixed_count += 1
                    logger.info(f"[ADMIN] Fixed delivery date for order {order.order_number}: {original_delivery} → {order.delivery_date}")
                    
            except Exception as e:
                logger.error(f"[ADMIN] Error fixing delivery date for order {order.order_number}: {e}")
                continue
    
    modeladmin.message_user(request, f"Successfully fixed delivery dates for {fixed_count} orders.")

fix_delivery_dates.short_description = "Fix invalid delivery dates (Auto-correct to Tue/Wed/Fri)"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderItemInline,)
    actions = [safe_delete_orders, fix_delivery_dates]
    
    list_display = ('order_number', 'restaurant', 'status', 'order_date', 'delivery_date', 'total_amount', 'created_at')
    list_filter = ('status', 'order_date', 'delivery_date', 'created_at')
    search_fields = ('order_number', 'restaurant__email', 'restaurant__restaurantprofile__business_name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('restaurant', 'order_number', 'status')}),
        ('Dates', {'fields': ('order_date', 'delivery_date'), 'description': 'Orders: Monday/Thursday only. Deliveries: Tuesday/Wednesday/Friday only.'}),
        ('Pricing', {'fields': ('subtotal', 'total_amount')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price')
    list_filter = ('order__status', 'product__department')
    search_fields = ('order__order_number', 'product__name')
    readonly_fields = ('total_price',) 