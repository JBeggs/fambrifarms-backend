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
    with transaction.atomic():
        for order in queryset:
            # Delete related objects that might cause constraints
            if hasattr(order, 'invoice') and order.invoice:
                order.invoice.delete()
            
            # Delete purchase orders
            order.purchase_orders.all().delete()
            
            # Delete order items (this should cascade properly)
            order.items.all().delete()
            
            # Finally delete the order
            order.delete()
    
    modeladmin.message_user(request, f"Successfully deleted {queryset.count()} orders and their related data.")

safe_delete_orders.short_description = "Safely delete selected orders"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderItemInline,)
    actions = [safe_delete_orders]
    
    list_display = ('order_number', 'restaurant', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'restaurant__email', 'restaurant__restaurantprofile__business_name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('restaurant', 'order_number', 'status')}),
        ('Pricing', {'fields': ('subtotal', 'total_amount')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price')
    list_filter = ('order__status', 'product__department')
    search_fields = ('order__order_number', 'product__name')
    readonly_fields = ('total_price',) 