from django.contrib import admin
from .models import (
    SystemSetting, CustomerSegment, OrderStatus, 
    StockAdjustmentType, BusinessConfiguration,
    UnitOfMeasure, MessageType, UserType, SupplierType,
    InvoiceStatus, PaymentMethod, ProductionStatus,
    QualityGrade, PriorityLevel, WhatsAppPattern,
    ProductVariation, CompanyAlias
)


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'category', 'is_active', 'updated_at']
    list_filter = ['category', 'is_active']
    search_fields = ['key', 'value', 'description']
    ordering = ['category', 'key']


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_markup', 'credit_limit_multiplier', 'payment_terms_days', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'color', 'is_final', 'sort_order', 'is_active']
    list_filter = ['is_final', 'is_active']
    search_fields = ['name', 'display_name']
    ordering = ['sort_order']


@admin.register(StockAdjustmentType)
class StockAdjustmentTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'affects_cost', 'requires_reason', 'is_active']
    list_filter = ['affects_cost', 'requires_reason', 'is_active']
    search_fields = ['name', 'display_name']
    ordering = ['name']


@admin.register(BusinessConfiguration)
class BusinessConfigurationAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'value_type', 'get_value', 'category', 'is_active']
    list_filter = ['value_type', 'category', 'is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['category', 'name']
    
    def get_value(self, obj):
        return obj.get_value()
    get_value.short_description = 'Current Value'


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'category', 'is_active', 'sort_order']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(MessageType)
class MessageTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'color', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(SupplierType)
class SupplierTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(InvoiceStatus)
class InvoiceStatusAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'color', 'is_final', 'is_active', 'sort_order']
    list_filter = ['is_final', 'is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'requires_reference', 'is_active', 'sort_order']
    list_filter = ['requires_reference', 'is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(ProductionStatus)
class ProductionStatusAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'color', 'is_final', 'is_active', 'sort_order']
    list_filter = ['is_final', 'is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(QualityGrade)
class QualityGradeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'color', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(PriorityLevel)
class PriorityLevelAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'color', 'numeric_value', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(WhatsAppPattern)
class WhatsAppPatternAdmin(admin.ModelAdmin):
    list_display = ['pattern_type', 'pattern_value', 'is_regex', 'is_active', 'sort_order']
    list_filter = ['pattern_type', 'is_regex', 'is_active']
    search_fields = ['pattern_type', 'pattern_value', 'description']
    ordering = ['pattern_type', 'sort_order', 'pattern_value']


@admin.register(ProductVariation)
class ProductVariationAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'normalized_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['original_name', 'normalized_name', 'description']
    ordering = ['original_name']


@admin.register(CompanyAlias)
class CompanyAliasAdmin(admin.ModelAdmin):
    list_display = ['alias', 'company_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['alias', 'company_name', 'description']
    ordering = ['alias']
