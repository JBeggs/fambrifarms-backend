from django.contrib import admin
from .models import (
    SystemSetting, CustomerSegment, OrderStatus, 
    StockAdjustmentType, BusinessConfiguration
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
