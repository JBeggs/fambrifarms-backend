from django.contrib import admin
from .models import Recipe, RecipeIngredient, ProductionBatch, ProductionReservation, QualityCheck

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'version', 'batch_size', 'production_time_minutes', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['product__name', 'name', 'version']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [RecipeIngredientInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'name', 'description', 'version')
        }),
        ('Production Details', {
            'fields': ('batch_size', 'production_time_minutes', 'yield_percentage')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ['recipe', 'raw_material', 'quantity', 'unit', 'is_optional']
    list_filter = ['is_optional', 'unit', 'recipe__product']
    search_fields = ['recipe__product__name', 'raw_material__name']

class ProductionReservationInline(admin.TabularInline):
    model = ProductionReservation
    extra = 0
    readonly_fields = ['quantity_remaining']

class QualityCheckInline(admin.TabularInline):
    model = QualityCheck
    extra = 0

@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_number', 'recipe', 'status', 'planned_quantity', 'actual_quantity', 'yield_percentage', 'planned_start_date']
    list_filter = ['status', 'planned_start_date', 'recipe__product']
    search_fields = ['batch_number', 'recipe__product__name', 'notes']
    readonly_fields = ['batch_number', 'yield_percentage', 'created_at', 'updated_at']
    inlines = [ProductionReservationInline, QualityCheckInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('batch_number', 'recipe', 'status')
        }),
        ('Quantities', {
            'fields': ('planned_quantity', 'actual_quantity', 'yield_percentage')
        }),
        ('Timing', {
            'fields': ('planned_start_date', 'planned_end_date', 'actual_start_date', 'actual_end_date')
        }),
        ('Staff & Notes', {
            'fields': ('produced_by', 'notes', 'quality_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ProductionReservation)
class ProductionReservationAdmin(admin.ModelAdmin):
    list_display = ['batch', 'raw_material', 'quantity_reserved', 'quantity_used', 'quantity_remaining', 'is_consumed']
    list_filter = ['is_consumed', 'batch__status']
    search_fields = ['batch__batch_number', 'raw_material__name']
    readonly_fields = ['quantity_remaining']

@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = ['batch', 'check_type', 'result', 'score', 'checked_by', 'check_date']
    list_filter = ['result', 'check_type', 'check_date']
    search_fields = ['batch__batch_number', 'check_type', 'notes']