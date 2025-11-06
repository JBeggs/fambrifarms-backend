from django.contrib import admin
from django.db import transaction
from django.contrib.admin import helpers
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price', 'confidence_score')
    fields = (
        'product', 'quantity', 'unit', 'price', 'total_price',
        'original_text', 'confidence_score', 'manually_corrected'
    )

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
    
    list_display = (
        'order_number_link', 'restaurant_link', 'status_colored',
        'order_date_formatted', 'delivery_date_formatted', 'total_amount_formatted',
        'item_count', 'ai_parsed_icon', 'created_at_formatted', 'updated_at_formatted'
    )
    list_filter = (
        'status', 'parsed_by_ai',
        ('order_date', admin.DateFieldListFilter),
        ('delivery_date', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
        'restaurant__user_type',
    )
    search_fields = (
        'order_number', 'restaurant__email', 'restaurant__first_name', 'restaurant__last_name',
        'restaurant__restaurantprofile__business_name', 'original_message'
    )
    readonly_fields = (
        'order_number', 'created_at', 'updated_at', 'item_count',
        'whatsapp_message_link', 'invoice_link'
    )
    date_hierarchy = 'order_date'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('restaurant', 'order_number', 'status')
        }),
        ('Scheduling', {
            'fields': ('order_date', 'delivery_date'),
            'description': 'Orders: Monday/Thursday only. Deliveries: Tuesday/Wednesday/Friday only.'
        }),
        ('Pricing', {
            'fields': ('subtotal', 'total_amount')
        }),
        ('WhatsApp Integration', {
            'fields': ('whatsapp_message_id', 'whatsapp_message_link', 'original_message', 'parsed_by_ai'),
            'classes': ('collapse',)
        }),
        ('Related Records', {
            'fields': ('item_count', 'invoice_link'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def order_number_link(self, obj):
        """Display order number as link"""
        return format_html(
            '<a href="{}" style="color: #0066cc; font-weight: bold;">{}</a>',
            reverse('admin:orders_order_change', args=[obj.pk]),
            obj.order_number
        )
    order_number_link.short_description = 'Order Number'
    order_number_link.admin_order_field = 'order_number'
    
    def restaurant_link(self, obj):
        """Display restaurant as link with business name"""
        display_name = obj.restaurant.email
        try:
            if hasattr(obj.restaurant, 'restaurantprofile') and obj.restaurant.restaurantprofile.business_name:
                display_name = obj.restaurant.restaurantprofile.business_name
                if obj.restaurant.restaurantprofile.branch_name:
                    display_name = f"{display_name} - {obj.restaurant.restaurantprofile.branch_name}"
        except:
            pass
        
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.restaurant.pk]),
            display_name
        )
    restaurant_link.short_description = 'Restaurant/Customer'
    restaurant_link.admin_order_field = 'restaurant__email'
    
    def status_colored(self, obj):
        """Display status with color coding"""
        colors = {
            'received': '#17a2b8',    # Teal
            'parsed': '#fd7e14',      # Orange
            'confirmed': '#ffc107',   # Yellow
            'po_sent': '#007bff',     # Blue
            'po_confirmed': '#6f42c1', # Purple
            'delivered': '#28a745',   # Green
            'cancelled': '#dc3545',   # Red
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    def order_date_formatted(self, obj):
        """Display order date with day name"""
        return format_html(
            '{}<br><small>{}</small>',
            obj.order_date.strftime('%Y-%m-%d'),
            obj.order_date.strftime('%A')
        )
    order_date_formatted.short_description = 'Order Date'
    order_date_formatted.admin_order_field = 'order_date'
    
    def delivery_date_formatted(self, obj):
        """Display delivery date with day name"""
        return format_html(
            '{}<br><small>{}</small>',
            obj.delivery_date.strftime('%Y-%m-%d'),
            obj.delivery_date.strftime('%A')
        )
    delivery_date_formatted.short_description = 'Delivery Date'
    delivery_date_formatted.admin_order_field = 'delivery_date'
    
    def total_amount_formatted(self, obj):
        """Format total amount"""
        return f'R{obj.total_amount:,.2f}'
    total_amount_formatted.short_description = 'Total Amount'
    total_amount_formatted.admin_order_field = 'total_amount'
    
    def item_count(self, obj):
        """Display number of items in order"""
        count = obj.items.count()
        if count > 0:
            return format_html(
                '<a href="{}?order__id__exact={}">{} items</a>',
                reverse('admin:orders_orderitem_changelist'),
                obj.pk,
                count
            )
        return '0 items'
    item_count.short_description = 'Items'
    
    def ai_parsed_icon(self, obj):
        """Display AI parsing status"""
        if obj.parsed_by_ai:
            return format_html('<span style="color: green; font-size: 12px;">🤖 AI Parsed</span>')
        return format_html('<span style="color: gray; font-size: 12px;">📝 Manual</span>')
    ai_parsed_icon.short_description = 'Parsing'
    ai_parsed_icon.admin_order_field = 'parsed_by_ai'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def updated_at_formatted(self, obj):
        """Format update date"""
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    updated_at_formatted.short_description = 'Updated'
    updated_at_formatted.admin_order_field = 'updated_at'
    
    def whatsapp_message_link(self, obj):
        """Link to related WhatsApp message"""
        if obj.whatsapp_message_id:
            try:
                from whatsapp.models import WhatsAppMessage
                message = WhatsAppMessage.objects.get(message_id=obj.whatsapp_message_id)
                return format_html(
                    '<a href="{}">View WhatsApp Message</a>',
                    reverse('admin:whatsapp_whatsappmessage_change', args=[message.pk])
                )
            except:
                pass
        return format_html('<em>No WhatsApp message</em>')
    whatsapp_message_link.short_description = 'WhatsApp Message'
    
    def invoice_link(self, obj):
        """Link to related invoice"""
        if hasattr(obj, 'invoice') and obj.invoice:
            return format_html(
                '<a href="{}">Invoice {}</a>',
                reverse('admin:invoices_invoice_change', args=[obj.invoice.pk]),
                obj.invoice.invoice_number
            )
        return format_html('<em>No invoice</em>')
    invoice_link.short_description = 'Invoice'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'restaurant', 'restaurant__restaurantprofile'
        ).prefetch_related('items', 'items__product')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order_link', 'product_link', 'quantity_unit', 'price_formatted',
        'total_price_formatted', 'confidence_indicator', 'manually_corrected_icon',
        'original_text_preview'
    )
    list_filter = (
        'order__status', 'product__department', 'manually_corrected',
        ('order__order_date', admin.DateFieldListFilter),
        ('order__delivery_date', admin.DateFieldListFilter),
    )
    search_fields = (
        'order__order_number', 'product__name', 'original_text',
        'order__restaurant__email', 'notes'
    )
    readonly_fields = ('total_price',)
    
    fieldsets = (
        ('Order Item Information', {
            'fields': ('order', 'product', 'quantity', 'unit', 'price', 'total_price')
        }),
        ('AI Parsing Details', {
            'fields': ('original_text', 'confidence_score', 'manually_corrected'),
            'classes': ('collapse',)
        }),
        ('Additional Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def order_link(self, obj):
        """Display order as link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:orders_order_change', args=[obj.order.pk]),
            obj.order.order_number
        )
    order_link.short_description = 'Order'
    order_link.admin_order_field = 'order__order_number'
    
    def product_link(self, obj):
        """Display product as link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:products_product_change', args=[obj.product.pk]),
            obj.product.name
        )
    product_link.short_description = 'Product'
    product_link.admin_order_field = 'product__name'
    
    def quantity_unit(self, obj):
        """Display quantity with unit"""
        return f'{obj.quantity} {obj.unit}'
    quantity_unit.short_description = 'Quantity'
    quantity_unit.admin_order_field = 'quantity'
    
    def price_formatted(self, obj):
        """Format price with currency"""
        return f'R{obj.price}'
    price_formatted.short_description = 'Unit Price'
    price_formatted.admin_order_field = 'price'
    
    def total_price_formatted(self, obj):
        """Format total price with currency"""
        return f'R{obj.total_price:,.2f}'
    total_price_formatted.short_description = 'Total Price'
    total_price_formatted.admin_order_field = 'total_price'
    
    def confidence_indicator(self, obj):
        """Display confidence score with color coding"""
        if obj.confidence_score >= 0.9:
            color = 'green'
            icon = '✓'
        elif obj.confidence_score >= 0.7:
            color = 'orange'
            icon = '~'
        else:
            color = 'red'
            icon = '⚠'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {:.0%}</span>',
            color, icon, obj.confidence_score
        )
    confidence_indicator.short_description = 'AI Confidence'
    confidence_indicator.admin_order_field = 'confidence_score'
    
    def manually_corrected_icon(self, obj):
        """Display manual correction status"""
        if obj.manually_corrected:
            return format_html('<span style="color: blue; font-size: 12px;">✏️ Corrected</span>')
        return format_html('<span style="color: gray; font-size: 12px;">🤖 Auto</span>')
    manually_corrected_icon.short_description = 'Source'
    manually_corrected_icon.admin_order_field = 'manually_corrected'
    
    def original_text_preview(self, obj):
        """Display preview of original text"""
        if obj.original_text:
            preview = obj.original_text[:30] + '...' if len(obj.original_text) > 30 else obj.original_text
            return format_html('<em>{}</em>', preview)
        return '-'
    original_text_preview.short_description = 'Original Text'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'order', 'product', 'product__department', 'order__restaurant'
        )