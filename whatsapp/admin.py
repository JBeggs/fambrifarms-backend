from django.contrib import admin
from .models import WhatsAppMessage, SalesRep, PurchaseOrder, POItem

@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['sender_name', 'message_text_short', 'processed', 'parsing_confidence', 'created_at']
    list_filter = ['processed', 'parsing_method', 'created_at']
    search_fields = ['sender_name', 'sender_phone', 'message_text']
    readonly_fields = ['message_id', 'created_at', 'processed_at']
    
    def message_text_short(self, obj):
        return obj.message_text[:50] + "..." if len(obj.message_text) > 50 else obj.message_text
    message_text_short.short_description = 'Message'

@admin.register(SalesRep)
class SalesRepAdmin(admin.ModelAdmin):
    list_display = ['name', 'whatsapp_number', 'is_active', 'total_orders_handled', 'response_rate']
    list_filter = ['is_active', 'specialties']
    search_fields = ['name', 'phone_number', 'whatsapp_number']

class POItemInline(admin.TabularInline):
    model = POItem
    extra = 0

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'sales_rep', 'status', 'estimated_total', 'confirmed_total', 'created_at']
    list_filter = ['status', 'sales_rep', 'created_at']
    search_fields = ['po_number', 'sales_rep__name']
    readonly_fields = ['po_number', 'created_at', 'sent_at', 'confirmed_at']
    inlines = [POItemInline]