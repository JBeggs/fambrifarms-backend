from rest_framework import serializers
from .models_business_settings import BusinessSettings, DepartmentKeyword
from inventory.serializers import UnitOfMeasureSerializer
from suppliers.serializers import SupplierSerializer

class BusinessSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for BusinessSettings - provides configurable defaults
    """
    
    # Read-only nested serializers for related objects
    default_weight_unit_detail = UnitOfMeasureSerializer(source='default_weight_unit', read_only=True)
    default_count_unit_detail = UnitOfMeasureSerializer(source='default_count_unit', read_only=True)
    default_department_name = serializers.CharField(source='default_department.name', read_only=True)
    default_supplier_name = serializers.CharField(source='default_supplier.name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = BusinessSettings
        fields = [
            'id',
            # Inventory defaults
            'default_minimum_level',
            'default_reorder_level', 
            'default_maximum_level',
            'default_order_quantity',
            
            # Price validation
            'max_price_variance_percent',
            'require_price_approval_above',
            
            # Tracking requirements
            'require_batch_tracking',
            'require_expiry_dates',
            'require_quality_grades',
            
            # Default units
            'default_weight_unit',
            'default_weight_unit_detail',
            'default_count_unit',
            'default_count_unit_detail',
            
            # Validation rules
            'min_phone_digits',
            'require_email_validation',
            
            # Department assignment
            'auto_assign_department',
            'default_department',
            'default_department_name',
            
            # Supplier management
            'default_supplier',
            'default_supplier_name',
            
            # System behavior
            'allow_negative_inventory',
            'auto_create_purchase_orders',
            
            # App configuration
            'django_base_url',
            'whatsapp_base_url',
            'default_base_markup',
            'default_volatility_adjustment',
            'default_trend_multiplier',
            'customer_segments',
            'api_timeout_seconds',
            'max_retry_attempts',
            'default_messages_limit',
            'default_stock_updates_limit',
            
            # Metadata
            'created_at',
            'updated_at',
            'updated_by',
            'updated_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'updated_by']


class DepartmentKeywordSerializer(serializers.ModelSerializer):
    """
    Serializer for DepartmentKeyword - for automatic department assignment
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = DepartmentKeyword
        fields = ['id', 'department', 'department_name', 'keyword', 'is_active']
        read_only_fields = ['id']


class AppConfigSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for app configuration settings only
    Used by Flutter app to get essential configuration
    Note: django_base_url is not included - it must be hardcoded in Flutter to avoid circular dependency
    """
    
    class Meta:
        model = BusinessSettings
        fields = [
            'whatsapp_base_url',
            'default_base_markup',
            'default_volatility_adjustment', 
            'default_trend_multiplier',
            'customer_segments',
            'api_timeout_seconds',
            'max_retry_attempts',
            'default_messages_limit',
            'default_stock_updates_limit'
        ]


class BusinessSettingsPublicSerializer(serializers.ModelSerializer):
    """
    Public serializer with only the settings needed by frontend
    No sensitive business information exposed
    """
    
    default_weight_unit_abbr = serializers.CharField(source='default_weight_unit.abbreviation', read_only=True)
    default_count_unit_abbr = serializers.CharField(source='default_count_unit.abbreviation', read_only=True)
    
    class Meta:
        model = BusinessSettings
        fields = [
            # Frontend needs these for form defaults
            'default_minimum_level',
            'default_reorder_level',
            'default_order_quantity',
            'default_weight_unit_abbr',
            'default_count_unit_abbr',
            'min_phone_digits',
            'require_email_validation',
            'auto_assign_department',
            
            # Validation flags
            'require_batch_tracking',
            'require_expiry_dates',
            'require_quality_grades',
        ]
