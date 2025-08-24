from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    UnitOfMeasure, RawMaterial, RawMaterialBatch, ProductionRecipe, 
    RecipeIngredient, FinishedInventory, StockMovement, ProductionBatch, 
    StockAlert
)


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'is_weight', 'base_unit_multiplier', 'is_active')
    list_filter = ('is_weight', 'is_active')
    search_fields = ('name', 'abbreviation')


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'unit', 'current_stock_display', 'reorder_level', 'needs_reorder_display', 'is_active')
    list_filter = ('is_active', 'requires_batch_tracking', 'unit')
    search_fields = ('name', 'sku')
    readonly_fields = ('current_stock_level', 'needs_reorder')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'sku', 'unit', 'is_active')
        }),
        ('Quality & Safety', {
            'fields': ('requires_batch_tracking', 'shelf_life_days', 'storage_temperature_min', 'storage_temperature_max')
        }),
        ('Inventory Levels', {
            'fields': ('minimum_stock_level', 'reorder_level', 'maximum_stock_level', 'current_stock_level', 'needs_reorder')
        }),
    )
    
    def current_stock_display(self, obj):
        stock = obj.current_stock_level
        if obj.needs_reorder:
            return format_html('<span style="color: red; font-weight: bold;">{} {}</span>', 
                             stock, obj.unit.abbreviation)
        return f"{stock} {obj.unit.abbreviation}"
    current_stock_display.short_description = 'Current Stock'
    
    def needs_reorder_display(self, obj):
        if obj.needs_reorder:
            return format_html('<span style="color: red;">⚠️ YES</span>')
        return format_html('<span style="color: green;">✓ No</span>')
    needs_reorder_display.short_description = 'Needs Reorder'


class RawMaterialBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'raw_material', 'supplier', 'received_quantity', 'available_quantity', 
                   'expiry_date', 'days_until_expiry_display', 'quality_grade', 'is_active')
    list_filter = ('quality_grade', 'is_active', 'received_date', 'expiry_date')
    search_fields = ('batch_number', 'raw_material__name', 'supplier__name')
    readonly_fields = ('total_cost', 'is_expired', 'days_until_expiry')
    date_hierarchy = 'received_date'
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_number', 'raw_material', 'supplier', 'quality_grade', 'is_active')
        }),
        ('Quantities', {
            'fields': ('received_quantity', 'available_quantity')
        }),
        ('Pricing', {
            'fields': ('unit_cost', 'total_cost')
        }),
        ('Dates', {
            'fields': ('received_date', 'production_date', 'expiry_date', 'is_expired', 'days_until_expiry')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def days_until_expiry_display(self, obj):
        days = obj.days_until_expiry
        if days is None:
            return "No expiry"
        if days < 0:
            return format_html('<span style="color: red; font-weight: bold;">EXPIRED ({} days ago)</span>', abs(days))
        elif days <= 3:
            return format_html('<span style="color: orange; font-weight: bold;">{} days</span>', days)
        elif days <= 7:
            return format_html('<span style="color: yellow;">{} days</span>', days)
        return f"{days} days"
    days_until_expiry_display.short_description = 'Days Until Expiry'


admin.site.register(RawMaterialBatch, RawMaterialBatchAdmin)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    readonly_fields = ('estimated_cost',)


@admin.register(ProductionRecipe)
class ProductionRecipeAdmin(admin.ModelAdmin):
    list_display = ('product', 'version', 'output_quantity', 'output_unit', 'cost_per_unit', 'is_active')
    list_filter = ('is_active', 'output_unit')
    search_fields = ('product__name', 'version')
    inlines = [RecipeIngredientInline]
    readonly_fields = ('total_raw_material_cost', 'cost_per_unit')
    
    fieldsets = (
        ('Recipe Details', {
            'fields': ('product', 'version', 'is_active')
        }),
        ('Output', {
            'fields': ('output_quantity', 'output_unit', 'yield_percentage')
        }),
        ('Processing', {
            'fields': ('processing_time_minutes', 'processing_notes')
        }),
        ('Costing', {
            'fields': ('total_raw_material_cost', 'cost_per_unit'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FinishedInventory)
class FinishedInventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'available_quantity', 'reserved_quantity', 'total_quantity', 
                   'minimum_level', 'needs_production_display', 'average_cost')
    list_filter = ('updated_at',)
    search_fields = ('product__name',)
    readonly_fields = ('total_quantity', 'needs_production', 'updated_at')
    
    def needs_production_display(self, obj):
        if obj.needs_production:
            return format_html('<span style="color: red;">⚠️ YES</span>')
        return format_html('<span style="color: green;">✓ No</span>')
    needs_production_display.short_description = 'Needs Production'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'movement_type', 'reference_number', 'item_display', 
                   'quantity', 'unit_cost', 'total_value', 'user')
    list_filter = ('movement_type', 'timestamp')
    search_fields = ('reference_number', 'raw_material__name', 'product__name')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    def item_display(self, obj):
        if obj.raw_material:
            return f"RM: {obj.raw_material.name}"
        elif obj.product:
            return f"Product: {obj.product.name}"
        return "Unknown"
    item_display.short_description = 'Item'
    
    def has_add_permission(self, request):
        # Stock movements should be created automatically by the system
        return False


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'recipe', 'planned_quantity', 'actual_quantity', 
                   'yield_percentage_display', 'status', 'planned_date', 'completed_at')
    list_filter = ('status', 'planned_date', 'completed_at')
    search_fields = ('batch_number', 'recipe__product__name')
    readonly_fields = ('yield_percentage', 'total_cost', 'cost_per_unit')
    date_hierarchy = 'planned_date'
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('batch_number', 'recipe', 'status')
        }),
        ('Quantities', {
            'fields': ('planned_quantity', 'actual_quantity', 'waste_quantity', 'yield_percentage')
        }),
        ('Timing', {
            'fields': ('planned_date', 'started_at', 'completed_at')
        }),
        ('People', {
            'fields': ('planned_by', 'produced_by')
        }),
        ('Costing', {
            'fields': ('total_raw_material_cost', 'labor_cost', 'overhead_cost', 'total_cost', 'cost_per_unit'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    def yield_percentage_display(self, obj):
        percentage = obj.yield_percentage
        if percentage < 80:
            return format_html('<span style="color: red;">{:.1f}%</span>', percentage)
        elif percentage < 90:
            return format_html('<span style="color: orange;">{:.1f}%</span>', percentage)
        return format_html('<span style="color: green;">{:.1f}%</span>', percentage)
    yield_percentage_display.short_description = 'Yield %'


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'alert_type', 'severity', 'item_display', 'message', 
                   'is_active', 'is_acknowledged', 'acknowledged_by')
    list_filter = ('alert_type', 'severity', 'is_active', 'is_acknowledged', 'created_at')
    search_fields = ('message', 'raw_material__name', 'product__name')
    readonly_fields = ('created_at', 'acknowledged_at')
    date_hierarchy = 'created_at'
    
    actions = ['mark_acknowledged']
    
    def item_display(self, obj):
        if obj.raw_material:
            return f"RM: {obj.raw_material.name}"
        elif obj.raw_material_batch:
            return f"Batch: {obj.raw_material_batch.batch_number}"
        elif obj.product:
            return f"Product: {obj.product.name}"
        return "System"
    item_display.short_description = 'Item'
    
    def mark_acknowledged(self, request, queryset):
        for alert in queryset:
            alert.acknowledge(request.user)
        self.message_user(request, f"{queryset.count()} alerts marked as acknowledged.")
    mark_acknowledged.short_description = "Mark selected alerts as acknowledged"


# Customize admin site header
admin.site.site_header = "Fambri Farms Inventory Management"
admin.site.site_title = "Fambri Farms Admin"
admin.site.index_title = "Welcome to Fambri Farms Inventory System"
