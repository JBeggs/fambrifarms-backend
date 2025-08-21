from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderItemInline,)
    
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