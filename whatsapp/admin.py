from django.contrib import admin
from .models import WhatsAppMessage, StockUpdate, OrderDayDemarcation, MessageProcessingLog

@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['sender_name', 'message_type', 'timestamp', 'processed', 'edited']
    list_filter = ['message_type', 'processed', 'edited', 'order_day', 'timestamp']
    search_fields = ['sender_name', 'content', 'sender_phone']
    readonly_fields = ['scraped_at', 'message_id']
    
    fieldsets = (
        ('Message Info', {
            'fields': ('message_id', 'chat_name', 'sender_name', 'sender_phone', 'timestamp', 'scraped_at')
        }),
        ('Content', {
            'fields': ('content', 'cleaned_content', 'original_content', 'edited')
        }),
        ('Classification', {
            'fields': ('message_type', 'confidence_score', 'order_day')
        }),
        ('Processing', {
            'fields': ('processed', 'order', 'parsed_items', 'instructions')
        }),
    )

@admin.register(StockUpdate)
class StockUpdateAdmin(admin.ModelAdmin):
    list_display = ['stock_date', 'order_day', 'processed', 'item_count', 'created_at']
    list_filter = ['order_day', 'processed', 'stock_date']
    readonly_fields = ['created_at', 'updated_at']
    
    def item_count(self, obj):
        return len(obj.items)
    item_count.short_description = 'Items Count'

@admin.register(OrderDayDemarcation)
class OrderDayDemarcationAdmin(admin.ModelAdmin):
    list_display = ['order_day', 'demarcation_date', 'active', 'orders_count']
    list_filter = ['order_day', 'active', 'demarcation_date']
    
    def orders_count(self, obj):
        return obj.orders_collected.count()
    orders_count.short_description = 'Orders Collected'

@admin.register(MessageProcessingLog)
class MessageProcessingLogAdmin(admin.ModelAdmin):
    list_display = ['message', 'action', 'timestamp', 'has_error']
    list_filter = ['action', 'timestamp']
    readonly_fields = ['timestamp']
    
    def has_error(self, obj):
        return bool(obj.error_message)
    has_error.boolean = True
    has_error.short_description = 'Has Error'
