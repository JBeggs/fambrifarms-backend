from django.contrib import admin
from .models import Supplier, SupplierProduct, SalesRep, SupplierPriceList, SupplierPriceListItem

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
            'fields': ('supplier', 'product', 'supplier_product_code', 'supplier_product_name', 'supplier_category_code')
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


@admin.register(SalesRep)
class SalesRepAdmin(admin.ModelAdmin):
    list_display = ['name', 'supplier', 'position', 'phone', 'email', 'is_active', 'is_primary']
    list_filter = ['is_active', 'is_primary', 'supplier', 'created_at']
    search_fields = ['name', 'email', 'phone', 'supplier__name']
    readonly_fields = ['created_at', 'updated_at']


class SupplierPriceListItemInline(admin.TabularInline):
    model = SupplierPriceListItem
    extra = 0
    readonly_fields = ['total_excl_vat', 'total_incl_vat', 'match_confidence', 'created_at']
    fields = [
        'supplier_code', 'product_description', 'category_code', 
        'quantity', 'unit_price', 'vat_amount', 'total_excl_vat', 'total_incl_vat',
        'matched_product', 'match_confidence', 'match_method', 'is_manually_matched',
        'is_new_product', 'needs_review'
    ]


@admin.register(SupplierPriceList)
class SupplierPriceListAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'list_date', 'received_date', 'is_processed', 'total_items', 'matched_items', 'match_percentage']
    list_filter = ['is_processed', 'supplier', 'list_date', 'received_date']
    search_fields = ['supplier__name', 'file_reference', 'notes']
    readonly_fields = ['received_date', 'created_at', 'updated_at', 'match_percentage']
    inlines = [SupplierPriceListItemInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('supplier', 'list_date', 'file_reference', 'notes')
        }),
        ('Processing Status', {
            'fields': ('is_processed', 'total_items', 'matched_items', 'unmatched_items', 'match_percentage')
        }),
        ('Timestamps', {
            'fields': ('received_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_processed', 'mark_as_unprocessed', 'run_matching']
    
    def mark_as_processed(self, request, queryset):
        queryset.update(is_processed=True)
    mark_as_processed.short_description = "Mark selected price lists as processed"
    
    def mark_as_unprocessed(self, request, queryset):
        queryset.update(is_processed=False)
    mark_as_unprocessed.short_description = "Mark selected price lists as unprocessed"
    
    def run_matching(self, request, queryset):
        # This will be implemented later with the matching algorithm
        self.message_user(request, "Matching algorithm not yet implemented")
    run_matching.short_description = "Run product matching on selected price lists"


@admin.register(SupplierPriceListItem)
class SupplierPriceListItemAdmin(admin.ModelAdmin):
    list_display = ['price_list', 'product_description', 'category_code', 'unit_price', 'matched_product', 'match_confidence', 'needs_review']
    list_filter = ['category_code', 'is_manually_matched', 'is_new_product', 'needs_review', 'price_list__supplier', 'match_method']
    search_fields = ['product_description', 'supplier_code', 'matched_product__name']
    readonly_fields = ['total_excl_vat', 'total_incl_vat', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Supplier Data', {
            'fields': ('price_list', 'supplier_code', 'product_description', 'category_code')
        }),
        ('Pricing', {
            'fields': ('quantity', 'unit_price', 'vat_amount', 'total_excl_vat', 'total_incl_vat')
        }),
        ('Product Matching', {
            'fields': ('matched_product', 'match_confidence', 'match_method', 'is_manually_matched')
        }),
        ('Status', {
            'fields': ('is_new_product', 'needs_review', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_new_product', 'mark_needs_review', 'clear_matching']
    
    def mark_as_new_product(self, request, queryset):
        queryset.update(is_new_product=True, needs_review=True)
    mark_as_new_product.short_description = "Mark as new product (needs review)"
    
    def mark_needs_review(self, request, queryset):
        queryset.update(needs_review=True)
    mark_needs_review.short_description = "Mark as needing review"
    
    def clear_matching(self, request, queryset):
        queryset.update(matched_product=None, match_confidence=None, match_method='', is_manually_matched=False)
    clear_matching.short_description = "Clear product matching"