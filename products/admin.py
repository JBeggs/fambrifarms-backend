from django.contrib import admin
from .models import Department, Product, ProductAlert, Recipe, MarketProcurementRecommendation, MarketProcurementItem

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'name': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'price', 'unit', 'needs_setup', 'is_active', 'created_at')
    list_filter = ('department', 'needs_setup', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_editable = ('price', 'needs_setup', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'department']
        }),
        ('Pricing & Inventory', {
            'fields': ['price', 'unit', 'stock_level', 'minimum_stock']
        }),
        ('Status', {
            'fields': ['needs_setup', 'is_active']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department')


@admin.register(ProductAlert)
class ProductAlertAdmin(admin.ModelAdmin):
    list_display = ('product', 'alert_type', 'is_resolved', 'created_at', 'resolved_by')
    list_filter = ('alert_type', 'is_resolved', 'created_at')
    search_fields = ('product__name', 'message')
    readonly_fields = ('created_at', 'resolved_at')
    
    fieldsets = [
        ('Alert Information', {
            'fields': ['product', 'alert_type', 'message', 'created_by_order']
        }),
        ('Resolution', {
            'fields': ['is_resolved', 'resolved_by', 'resolved_at']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'resolved_by')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('product', 'yield_quantity', 'yield_unit', 'prep_time_minutes', 'created_at')
    search_fields = ('product__name', 'instructions')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = [
        ('Product Information', {
            'fields': ['product']
        }),
        ('Recipe Details', {
            'fields': ['ingredients', 'instructions', 'prep_time_minutes']
        }),
        ('Yield Information', {
            'fields': ['yield_quantity', 'yield_unit']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


class MarketProcurementItemInline(admin.TabularInline):
    model = MarketProcurementItem
    extra = 0
    fields = ('product', 'needed_quantity', 'recommended_quantity', 'estimated_unit_price', 'estimated_total_cost', 'priority')
    readonly_fields = ('estimated_total_cost',)


@admin.register(MarketProcurementRecommendation)
class MarketProcurementRecommendationAdmin(admin.ModelAdmin):
    list_display = ('for_date', 'status', 'total_estimated_cost', 'items_count', 'approved_by', 'created_at')
    list_filter = ('status', 'for_date', 'created_at')
    search_fields = ('notes',)
    readonly_fields = ('created_at', 'approved_at', 'total_estimated_cost')
    inlines = [MarketProcurementItemInline]
    
    fieldsets = [
        ('Trip Information', {
            'fields': ['for_date', 'status', 'total_estimated_cost']
        }),
        ('Approval', {
            'fields': ['approved_by', 'approved_at']
        }),
        ('Analysis', {
            'fields': ['analysis_data', 'notes'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at'],
            'classes': ['collapse']
        })
    ]
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('approved_by').prefetch_related('items') 