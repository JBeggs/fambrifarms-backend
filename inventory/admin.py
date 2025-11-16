from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    UnitOfMeasure, RawMaterial, RawMaterialBatch, ProductionRecipe, 
    RecipeIngredient, FinishedInventory, StockMovement, ProductionBatch, 
    StockAlert, StockAnalysis, StockAnalysisItem, MarketPrice, 
    ProcurementRecommendation, PriceAlert, PricingRule, CustomerPriceList,
    CustomerPriceListItem, WeeklyPriceReport
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
    list_filter = ('quality_grade', 'is_active', 'received_date', 'expiry_date', 'supplier')
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
                   'minimum_level', 'needs_production_display', 'average_cost', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('product__name',)
    readonly_fields = ('total_quantity', 'needs_production', 'updated_at')
    date_hierarchy = 'updated_at'
    
    def needs_production_display(self, obj):
        if obj.needs_production:
            return format_html('<span style="color: red;">⚠️ YES</span>')
        return format_html('<span style="color: green;">✓ No</span>')
    needs_production_display.short_description = 'Needs Production'


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'movement_type', 'reference_number', 'item_display', 
                   'quantity', 'weight', 'unit_cost', 'total_value', 'user')
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


class StockAnalysisItemInline(admin.TabularInline):
    model = StockAnalysisItem
    extra = 0
    readonly_fields = ('shortfall_quantity', 'needs_procurement', 'urgency_level', 'shortfall_value', 'fulfillment_percentage')
    fields = ('product', 'total_ordered_quantity', 'available_stock_quantity', 'unit_price', 
             'shortfall_quantity', 'needs_procurement', 'urgency_level', 'suggested_order_quantity', 'suggested_supplier')


@admin.register(StockAnalysis)
class StockAnalysisAdmin(admin.ModelAdmin):
    list_display = ('analysis_date', 'order_period_start', 'order_period_end', 'status', 
                   'fulfillment_percentage', 'total_orders_value', 'shortfall_value', 'created_by')
    list_filter = ('status', 'analysis_date', 'order_period_start')
    search_fields = ('notes',)
    readonly_fields = ('analysis_date', 'shortfall_value', 'items_needing_procurement_count')
    date_hierarchy = 'analysis_date'
    inlines = [StockAnalysisItemInline]
    
    fieldsets = (
        ('Analysis Period', {
            'fields': ('order_period_start', 'order_period_end', 'status')
        }),
        ('Results', {
            'fields': ('total_orders_value', 'total_stock_value', 'fulfillment_percentage', 'shortfall_value')
        }),
        ('Metadata', {
            'fields': ('analysis_date', 'created_by', 'notes', 'items_needing_procurement_count')
        }),
    )
    
    def items_needing_procurement_count(self, obj):
        count = obj.items_needing_procurement.count()
        if count > 0:
            return format_html('<span style="color: red; font-weight: bold;">{} items</span>', count)
        return format_html('<span style="color: green;">0 items</span>')
    items_needing_procurement_count.short_description = 'Items Needing Procurement'


@admin.register(StockAnalysisItem)
class StockAnalysisItemAdmin(admin.ModelAdmin):
    list_display = ('analysis', 'product', 'total_ordered_quantity', 'available_stock_quantity', 
                   'shortfall_quantity', 'urgency_level', 'needs_procurement', 'suggested_supplier')
    list_filter = ('urgency_level', 'needs_procurement', 'analysis__analysis_date')
    search_fields = ('product__name', 'analysis__notes')
    readonly_fields = ('shortfall_quantity', 'needs_procurement', 'urgency_level', 'shortfall_value', 'fulfillment_percentage')
    
    fieldsets = (
        ('Analysis', {
            'fields': ('analysis', 'product')
        }),
        ('Demand vs Supply', {
            'fields': ('total_ordered_quantity', 'available_stock_quantity', 'shortfall_quantity', 'unit_price')
        }),
        ('Analysis Results', {
            'fields': ('needs_procurement', 'urgency_level', 'shortfall_value', 'fulfillment_percentage')
        }),
        ('Recommendations', {
            'fields': ('suggested_order_quantity', 'suggested_supplier')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('analysis', 'product', 'suggested_supplier')


# Market Price and Procurement Intelligence Admin

@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'supplier_name', 'invoice_date', 'unit_price_incl_vat', 
                   'matched_product', 'vat_percentage_display', 'is_active')
    list_filter = ('supplier_name', 'invoice_date', 'is_active', 'quantity_unit')
    search_fields = ('product_name', 'matched_product__name', 'invoice_reference')
    date_hierarchy = 'invoice_date'
    readonly_fields = ('created_at', 'updated_at', 'vat_percentage_display')
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('supplier_name', 'invoice_date', 'invoice_reference')
        }),
        ('Product Information', {
            'fields': ('product_name', 'matched_product', 'quantity_unit')
        }),
        ('Pricing Details', {
            'fields': ('unit_price_excl_vat', 'vat_amount', 'unit_price_incl_vat', 'vat_percentage_display')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def vat_percentage_display(self, obj):
        return f"{obj.vat_percentage:.1f}%"
    vat_percentage_display.short_description = 'VAT %'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('matched_product')


class ProcurementRecommendationInline(admin.TabularInline):
    model = ProcurementRecommendation
    extra = 0
    readonly_fields = ('estimated_total_cost', 'days_until_order', 'is_overdue_display')
    fields = ('product', 'recommended_quantity', 'recommended_supplier', 'current_market_price',
             'urgency_level', 'recommended_order_date', 'status', 'estimated_total_cost')
    
    def days_until_order(self, obj):
        days = obj.days_until_recommended_order
        if days < 0:
            return f"⚠️ {abs(days)} days overdue"
        elif days == 0:
            return "📅 Today"
        else:
            return f"📅 {days} days"
    days_until_order.short_description = 'Order Timing'
    
    def is_overdue_display(self, obj):
        return "🚨 Overdue" if obj.is_overdue else "✅ On Time"
    is_overdue_display.short_description = 'Status'


@admin.register(ProcurementRecommendation)
class ProcurementRecommendationAdmin(admin.ModelAdmin):
    list_display = ('product', 'recommended_quantity', 'urgency_level', 'recommended_order_date',
                   'status', 'estimated_total_cost', 'days_until_order', 'is_overdue_display')
    list_filter = ('urgency_level', 'status', 'price_trend', 'recommended_order_date', 'stock_analysis__analysis_date')
    search_fields = ('product__name', 'recommended_supplier__name', 'notes')
    date_hierarchy = 'recommended_order_date'
    readonly_fields = ('estimated_total_cost', 'days_until_order', 'is_overdue_display', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('stock_analysis', 'product', 'created_by')
        }),
        ('Recommendation Details', {
            'fields': ('recommended_quantity', 'recommended_supplier', 'urgency_level', 
                      'recommended_order_date', 'expected_delivery_date')
        }),
        ('Market Intelligence', {
            'fields': ('current_market_price', 'average_market_price_30d', 'price_trend')
        }),
        ('Financial Analysis', {
            'fields': ('estimated_total_cost', 'potential_savings')
        }),
        ('Status & Timing', {
            'fields': ('status', 'days_until_order', 'is_overdue_display', 'created_at', 'updated_at')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def days_until_order(self, obj):
        days = obj.days_until_recommended_order
        if days < 0:
            return f"⚠️ {abs(days)} days overdue"
        elif days == 0:
            return "📅 Today"
        else:
            return f"📅 {days} days"
    days_until_order.short_description = 'Order Timing'
    
    def is_overdue_display(self, obj):
        return "🚨 Overdue" if obj.is_overdue else "✅ On Time"
    is_overdue_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'recommended_supplier', 'stock_analysis', 'created_by')


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'alert_type', 'price_change_display', 'current_price', 
                   'alert_triggered_at', 'is_acknowledged', 'acknowledged_by')
    list_filter = ('alert_type', 'is_acknowledged', 'alert_triggered_at')
    search_fields = ('product__name', 'recommended_action')
    date_hierarchy = 'alert_triggered_at'
    readonly_fields = ('alert_triggered_at', 'acknowledged_at', 'price_change_display')
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('product', 'alert_type', 'threshold_percentage')
        }),
        ('Price Data', {
            'fields': ('baseline_price', 'current_price', 'price_change_display')
        }),
        ('Alert Status', {
            'fields': ('alert_triggered_at', 'is_acknowledged', 'acknowledged_by', 'acknowledged_at')
        }),
        ('Recommendation', {
            'fields': ('recommended_action',),
            'classes': ('collapse',)
        }),
    )
    
    def price_change_display(self, obj):
        change = obj.price_change_percentage
        if change > 0:
            return f"📈 +{change:.1f}%"
        else:
            return f"📉 {change:.1f}%"
    price_change_display.short_description = 'Price Change'
    
    actions = ['acknowledge_alerts']
    
    def acknowledge_alerts(self, request, queryset):
        for alert in queryset.filter(is_acknowledged=False):
            alert.acknowledge(request.user)
        self.message_user(request, f"Acknowledged {queryset.count()} alerts.")
    acknowledge_alerts.short_description = "Acknowledge selected alerts"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'acknowledged_by')


# Update StockAnalysisAdmin to include procurement recommendations
# Add the inline to existing StockAnalysisAdmin
try:
    # Get the existing admin class
    existing_admin = admin.site._registry[StockAnalysis]
    # Add our inline to the existing inlines
    if hasattr(existing_admin, 'inlines'):
        existing_admin.inlines = list(existing_admin.inlines) + [ProcurementRecommendationInline]
    else:
        existing_admin.inlines = [ProcurementRecommendationInline]
except KeyError:
    # StockAnalysis admin doesn't exist yet, will be handled when it's registered
    pass


# Dynamic Price Management Admin

@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_segment', 'base_markup_percentage', 'volatility_adjustment', 
                   'is_active', 'effective_from', 'effective_until')
    list_filter = ('customer_segment', 'is_active', 'effective_from')
    search_fields = ('name', 'description')
    date_hierarchy = 'effective_from'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'customer_segment', 'created_by')
        }),
        ('Markup Configuration', {
            'fields': ('base_markup_percentage', 'volatility_adjustment', 'minimum_margin_percentage')
        }),
        ('Advanced Adjustments', {
            'fields': ('category_adjustments', 'trend_multiplier', 'seasonal_adjustment'),
            'classes': ('collapse',)
        }),
        ('Validity Period', {
            'fields': ('is_active', 'effective_from', 'effective_until')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


class CustomerPriceListItemInline(admin.TabularInline):
    model = CustomerPriceListItem
    extra = 0
    readonly_fields = ('margin_amount', 'is_price_increase', 'is_significant_change')
    fields = ('product', 'market_price_incl_vat', 'markup_percentage', 'customer_price_incl_vat',
             'price_change_percentage', 'is_volatile', 'is_premium')
    
    def margin_amount(self, obj):
        return f"R{obj.margin_amount:.2f}"
    margin_amount.short_description = 'Margin'
    
    def is_price_increase(self, obj):
        return "📈" if obj.is_price_increase else "📉"
    is_price_increase.short_description = 'Trend'
    
    def is_significant_change(self, obj):
        return "⚠️" if obj.is_significant_change else "✅"
    is_significant_change.short_description = 'Change'


@admin.register(CustomerPriceList)
class CustomerPriceListAdmin(admin.ModelAdmin):
    list_display = ('list_name', 'customer_name', 'status', 'effective_from', 'effective_until',
                   'total_products', 'average_markup_percentage', 'is_current')
    list_filter = ('status', 'effective_from', 'pricing_rule__customer_segment', 'market_data_source')
    search_fields = ('list_name', 'customer__first_name', 'customer__last_name', 'customer__email')
    date_hierarchy = 'effective_from'
    readonly_fields = ('generated_at', 'is_current', 'days_until_expiry')
    inlines = [CustomerPriceListItemInline]
    
    fieldsets = (
        ('Customer & Rule', {
            'fields': ('customer', 'pricing_rule', 'list_name')
        }),
        ('Validity Period', {
            'fields': ('effective_from', 'effective_until', 'is_current', 'days_until_expiry')
        }),
        ('Market Data Source', {
            'fields': ('based_on_market_data', 'market_data_source')
        }),
        ('Statistics', {
            'fields': ('total_products', 'average_markup_percentage', 'total_list_value')
        }),
        ('Status & Delivery', {
            'fields': ('status', 'sent_at', 'acknowledged_at')
        }),
        ('Generation Info', {
            'fields': ('generated_by', 'generated_at', 'notes'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        return obj.customer.get_full_name()
    customer_name.short_description = 'Customer'
    
    def is_current(self, obj):
        return "✅ Current" if obj.is_current else "❌ Expired"
    is_current.short_description = 'Status'
    
    actions = ['activate_price_lists', 'send_to_customers']
    
    def activate_price_lists(self, request, queryset):
        for price_list in queryset:
            price_list.activate()
        self.message_user(request, f"Activated {queryset.count()} price lists.")
    activate_price_lists.short_description = "Activate selected price lists"
    
    def send_to_customers(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='sent', sent_at=timezone.now())
        self.message_user(request, f"Marked {queryset.count()} price lists as sent.")
    send_to_customers.short_description = "Mark as sent to customers"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'pricing_rule', 'generated_by')


@admin.register(CustomerPriceListItem)
class CustomerPriceListItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price_list_customer', 'market_price_incl_vat', 'markup_percentage',
                   'customer_price_incl_vat', 'price_change_display', 'is_volatile', 'is_premium')
    list_filter = ('is_volatile', 'is_premium', 'is_seasonal', 'price_list__status')
    search_fields = ('product__name', 'price_list__customer__first_name', 'price_list__customer__last_name')
    readonly_fields = ('margin_amount', 'is_price_increase', 'is_significant_change')
    
    fieldsets = (
        ('Product & Price List', {
            'fields': ('price_list', 'product')
        }),
        ('Market Price', {
            'fields': ('market_price_excl_vat', 'market_price_incl_vat', 'market_price_date')
        }),
        ('Customer Price', {
            'fields': ('markup_percentage', 'customer_price_excl_vat', 'customer_price_incl_vat')
        }),
        ('Price Change Analysis', {
            'fields': ('previous_price', 'price_change_percentage', 'margin_amount', 
                      'is_price_increase', 'is_significant_change')
        }),
        ('Product Characteristics', {
            'fields': ('unit_of_measure', 'product_category', 'is_volatile', 'is_seasonal', 'is_premium')
        }),
    )
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product'
    
    def price_list_customer(self, obj):
        return obj.price_list.customer.get_full_name()
    price_list_customer.short_description = 'Customer'
    
    def price_change_display(self, obj):
        change = obj.price_change_percentage
        if change > 0:
            return f"📈 +{change:.1f}%"
        elif change < 0:
            return f"📉 {change:.1f}%"
        else:
            return "➡️ 0%"
    price_change_display.short_description = 'Price Change'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'price_list__customer')


@admin.register(WeeklyPriceReport)
class WeeklyPriceReportAdmin(admin.ModelAdmin):
    list_display = ('report_name', 'week_number', 'year', 'status', 'total_customers_affected',
                   'average_price_increase', 'most_volatile_product', 'generated_at')
    list_filter = ('status', 'report_week_start')
    search_fields = ('report_name', 'most_volatile_product')
    date_hierarchy = 'report_week_start'
    readonly_fields = ('generated_at', 'week_number', 'year')
    
    fieldsets = (
        ('Report Information', {
            'fields': ('report_name', 'report_week_start', 'report_week_end', 'week_number', 'year')
        }),
        ('Market Analysis', {
            'fields': ('total_market_prices_analyzed', 'average_market_volatility', 
                      'most_volatile_product', 'most_volatile_percentage')
        }),
        ('Customer Impact', {
            'fields': ('total_price_lists_generated', 'total_customers_affected', 'average_price_increase')
        }),
        ('Procurement Analysis', {
            'fields': ('total_procurement_recommendations', 'estimated_procurement_cost', 
                      'potential_savings_identified')
        }),
        ('Key Insights', {
            'fields': ('key_insights',),
            'classes': ('collapse',)
        }),
        ('Report Status', {
            'fields': ('status', 'generated_by', 'generated_at')
        }),
    )
    
    def week_number(self, obj):
        return obj.week_number
    week_number.short_description = 'Week #'
    
    def year(self, obj):
        return obj.year
    year.short_description = 'Year'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('generated_by')


# Customize admin site header
admin.site.site_header = "Fambri Farms Inventory Management"
admin.site.site_title = "Fambri Farms Admin"
admin.site.index_title = "Welcome to Fambri Farms Inventory System"
