from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderReceipt, PurchaseOrderReceiptItem

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ['total_price']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'status', 'order_date', 'expected_delivery_date', 'total_amount', 'created_at']
    list_filter = ['status', 'order_date', 'supplier', 'created_at']
    search_fields = ['po_number', 'supplier__name', 'notes']
    readonly_fields = ['po_number', 'created_at', 'updated_at']
    inlines = [PurchaseOrderItemInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('po_number', 'supplier', 'order', 'status')
        }),
        ('Dates', {
            'fields': ('order_date', 'expected_delivery_date', 'actual_delivery_date')
        }),
        ('Financial', {
            'fields': ('subtotal', 'tax_amount', 'total_amount')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'product', 'quantity_ordered', 'quantity_received', 'unit_price', 'total_price']
    list_filter = ['purchase_order__status', 'product', 'created_at']
    search_fields = ['purchase_order__po_number', 'product__name']
    readonly_fields = ['total_price', 'quantity_pending', 'is_fully_received', 'created_at', 'updated_at']

class PurchaseOrderReceiptItemInline(admin.TabularInline):
    model = PurchaseOrderReceiptItem
    extra = 0

@admin.register(PurchaseOrderReceipt)
class PurchaseOrderReceiptAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'received_date', 'received_by', 'quality_check_passed', 'delivery_note_number']
    list_filter = ['quality_check_passed', 'received_date', 'purchase_order__supplier']
    search_fields = ['purchase_order__po_number', 'delivery_note_number', 'invoice_number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PurchaseOrderReceiptItemInline]
    
    fieldsets = (
        ('Receipt Information', {
            'fields': ('purchase_order', 'received_by', 'received_date')
        }),
        ('Quality Control', {
            'fields': ('quality_check_passed', 'quality_notes')
        }),
        ('Documentation', {
            'fields': ('delivery_note_number', 'invoice_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PurchaseOrderReceiptItem)
class PurchaseOrderReceiptItemAdmin(admin.ModelAdmin):
    list_display = ['receipt', 'po_item', 'quantity_received', 'condition_rating']
    list_filter = ['condition_rating', 'receipt__received_date']
    search_fields = ['receipt__purchase_order__po_number', 'po_item__product__name']