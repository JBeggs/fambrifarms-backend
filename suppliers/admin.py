from django.contrib import admin
from .models import Supplier, SupplierProduct

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'is_active', 'lead_time_days', 'created_at']
    list_filter = ['is_active', 'lead_time_days', 'created_at']
    search_fields = ['name', 'contact_person', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'contact_person', 'email', 'phone', 'address')
        }),
        ('Business Details', {
            'fields': ('registration_number', 'tax_number', 'payment_terms_days', 'lead_time_days', 'minimum_order_value')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'product', 'supplier_price', 'is_available', 'stock_quantity', 'quality_rating', 'last_order_date']
    list_filter = ['is_available', 'supplier', 'product__department', 'created_at']
    search_fields = ['supplier__name', 'product__name', 'supplier_product_code', 'supplier_product_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('supplier', 'product', 'supplier_product_code', 'supplier_product_name')
        }),
        ('Pricing & Availability', {
            'fields': ('supplier_price', 'currency', 'is_available', 'stock_quantity', 'minimum_order_quantity')
        }),
        ('Performance', {
            'fields': ('quality_rating', 'last_order_date', 'lead_time_days')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )