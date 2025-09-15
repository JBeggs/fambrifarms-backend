from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import (
    UnitOfMeasure, RawMaterial, RawMaterialBatch, ProductionRecipe, 
    RecipeIngredient, FinishedInventory, StockMovement, ProductionBatch, 
    StockAlert, StockAnalysis, StockAnalysisItem, MarketPrice, 
    ProcurementRecommendation, PriceAlert, PricingRule, CustomerPriceList,
    CustomerPriceListItem, WeeklyPriceReport
)
from products.models import Product
from suppliers.models import Supplier

User = get_user_model()


class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = '__all__'
        read_only_fields = ['id']


class RawMaterialListSerializer(serializers.ModelSerializer):
    """Simplified serializer for lists"""
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    unit_abbreviation = serializers.CharField(source='unit.abbreviation', read_only=True)
    current_stock_level = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = RawMaterial
        fields = [
            'id', 'name', 'sku', 'unit', 'unit_name', 'unit_abbreviation',
            'current_stock_level', 'needs_reorder', 'minimum_stock_level', 
            'reorder_level', 'is_active'
        ]


class RawMaterialDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual raw materials"""
    unit = UnitOfMeasureSerializer(read_only=True)
    unit_id = serializers.IntegerField(write_only=True)
    current_stock_level = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)
    active_batches_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RawMaterial
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_active_batches_count(self, obj):
        return obj.batches.filter(is_active=True, available_quantity__gt=0).count()


class RawMaterialBatchListSerializer(serializers.ModelSerializer):
    """Simplified serializer for batch lists"""
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    raw_material_sku = serializers.CharField(source='raw_material.sku', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = RawMaterialBatch
        fields = [
            'id', 'batch_number', 'raw_material', 'raw_material_name', 'raw_material_sku',
            'supplier', 'supplier_name', 'received_quantity', 'available_quantity',
            'unit_cost', 'received_date', 'expiry_date', 'days_until_expiry',
            'is_expired', 'quality_grade', 'is_active'
        ]


class RawMaterialBatchDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual batches"""
    raw_material = RawMaterialListSerializer(read_only=True)
    raw_material_id = serializers.IntegerField(write_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = RawMaterialBatch
        fields = '__all__'
        read_only_fields = ['id', 'total_cost']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    raw_material_unit = serializers.CharField(source='raw_material.unit.abbreviation', read_only=True)
    estimated_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = RecipeIngredient
        fields = '__all__'
        read_only_fields = ['id']


class ProductionRecipeListSerializer(serializers.ModelSerializer):
    """Simplified serializer for recipe lists"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    output_unit_name = serializers.CharField(source='output_unit.abbreviation', read_only=True)
    total_raw_material_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cost_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    ingredients_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductionRecipe
        fields = [
            'id', 'product', 'product_name', 'version', 'output_quantity', 
            'output_unit', 'output_unit_name', 'total_raw_material_cost',
            'cost_per_unit', 'ingredients_count', 'is_active', 'created_at'
        ]
    
    def get_ingredients_count(self, obj):
        return obj.ingredients.count()


class ProductionRecipeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual recipes"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    output_unit = UnitOfMeasureSerializer(read_only=True)
    output_unit_id = serializers.IntegerField(write_only=True)
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    total_raw_material_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cost_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = ProductionRecipe
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def create(self, validated_data):
        # Set the created_by field to the current user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class FinishedInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    total_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    needs_production = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = FinishedInventory
        fields = '__all__'
        read_only_fields = ['id', 'updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    batch_number = serializers.CharField(source='raw_material_batch.batch_number', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']


class ProductionBatchListSerializer(serializers.ModelSerializer):
    """Simplified serializer for production batch lists"""
    recipe_product_name = serializers.CharField(source='recipe.product.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    yield_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    cost_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    planned_by_name = serializers.CharField(source='planned_by.get_full_name', read_only=True)
    
    class Meta:
        model = ProductionBatch
        fields = [
            'id', 'batch_number', 'recipe', 'recipe_product_name', 'status', 
            'status_display', 'planned_quantity', 'actual_quantity', 'waste_quantity',
            'yield_percentage', 'cost_per_unit', 'planned_date', 'completed_at',
            'planned_by_name'
        ]


class ProductionBatchDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual production batches"""
    recipe_detail = ProductionRecipeListSerializer(source='recipe', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    yield_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cost_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    planned_by_name = serializers.CharField(source='planned_by.get_full_name', read_only=True)
    produced_by_name = serializers.CharField(source='produced_by.get_full_name', read_only=True)
    
    class Meta:
        model = ProductionBatch
        fields = '__all__'
        read_only_fields = ['id', 'batch_number']
    
    def create(self, validated_data):
        # Set the planned_by field to the current user
        validated_data['planned_by'] = self.context['request'].user
        return super().create(validated_data)


class StockAlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    batch_number = serializers.CharField(source='raw_material_batch.batch_number', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockAlert
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'acknowledged_at']


# Dashboard and Summary Serializers
class InventoryDashboardSerializer(serializers.Serializer):
    """Dashboard summary data"""
    total_products = serializers.IntegerField()
    total_raw_materials = serializers.IntegerField()
    low_stock_alerts = serializers.IntegerField()
    expiring_batches = serializers.IntegerField()
    active_production_batches = serializers.IntegerField()
    total_stock_value = serializers.DecimalField(max_digits=12, decimal_places=2)


class StockLevelSerializer(serializers.Serializer):
    """Stock level summary for products"""
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    department = serializers.CharField()
    available_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    reserved_quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    reorder_level = serializers.DecimalField(max_digits=10, decimal_places=2)
    needs_production = serializers.BooleanField()
    average_cost = serializers.DecimalField(max_digits=10, decimal_places=2)


# Action Serializers for specific operations
class StockReservationSerializer(serializers.Serializer):
    """For reserving/releasing stock"""
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    reference_number = serializers.CharField(max_length=50)
    notes = serializers.CharField(max_length=500, required=False)


class ProductionStartSerializer(serializers.Serializer):
    """For starting production batches"""
    batch_id = serializers.IntegerField()
    actual_start_time = serializers.DateTimeField(required=False)
    notes = serializers.CharField(max_length=500, required=False)


class ProductionCompleteSerializer(serializers.Serializer):
    """For completing production batches"""
    batch_id = serializers.IntegerField()
    actual_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'))
    waste_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'), required=False, allow_null=True)
    actual_completion_time = serializers.DateTimeField(required=False)
    labor_cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'), required=False, allow_null=True)
    overhead_cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0'), required=False, allow_null=True)
    notes = serializers.CharField(max_length=500, required=False)


class StockAdjustmentSerializer(serializers.Serializer):
    """For manual stock adjustments"""
    adjustment_type = serializers.ChoiceField(choices=[
        ('finished_adjust', 'Finished Inventory Adjustment'),
        ('finished_waste', 'Finished Product Waste'),
        ('raw_adjust', 'Raw Material Adjustment'),
        ('raw_waste', 'Raw Material Waste'),
    ])
    product_id = serializers.IntegerField(required=False)
    raw_material_id = serializers.IntegerField(required=False)
    batch_id = serializers.IntegerField(required=False)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField(max_length=200)
    notes = serializers.CharField(max_length=500, required=False)
    
    def validate(self, data):
        adjustment_type = data.get('adjustment_type')
        
        if adjustment_type in ['finished_adjust', 'finished_waste']:
            if not data.get('product_id'):
                raise serializers.ValidationError("product_id is required for finished inventory adjustments")
        
        elif adjustment_type in ['raw_adjust', 'raw_waste']:
            if not data.get('raw_material_id'):
                raise serializers.ValidationError("raw_material_id is required for raw material adjustments")
        
        return data


class StockAnalysisItemSerializer(serializers.ModelSerializer):
    """Serializer for individual stock analysis items"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    suggested_supplier_name = serializers.CharField(source='suggested_supplier.name', read_only=True)
    shortfall_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    fulfillment_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = StockAnalysisItem
        fields = [
            'id', 'product', 'product_name', 'product_department',
            'total_ordered_quantity', 'available_stock_quantity', 'shortfall_quantity',
            'unit_price', 'needs_procurement', 'suggested_order_quantity',
            'suggested_supplier', 'suggested_supplier_name', 'urgency_level',
            'shortfall_value', 'fulfillment_percentage'
        ]
        read_only_fields = ['shortfall_quantity', 'needs_procurement', 'urgency_level']


class StockAnalysisListSerializer(serializers.ModelSerializer):
    """Simplified serializer for stock analysis lists"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    shortfall_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    items_needing_procurement_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StockAnalysis
        fields = [
            'id', 'analysis_date', 'order_period_start', 'order_period_end',
            'status', 'total_orders_value', 'total_stock_value', 'fulfillment_percentage',
            'shortfall_value', 'created_by_name', 'items_needing_procurement_count'
        ]
    
    def get_items_needing_procurement_count(self, obj):
        return obj.items_needing_procurement.count()


class StockAnalysisDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual stock analysis"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    shortfall_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    items = StockAnalysisItemSerializer(many=True, read_only=True)
    items_needing_procurement = StockAnalysisItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = StockAnalysis
        fields = [
            'id', 'analysis_date', 'order_period_start', 'order_period_end',
            'status', 'total_orders_value', 'total_stock_value', 'fulfillment_percentage',
            'shortfall_value', 'created_by', 'created_by_name', 'notes',
            'items', 'items_needing_procurement'
        ]
        read_only_fields = ['analysis_date', 'shortfall_value']


class StockAnalysisCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new stock analysis"""
    
    class Meta:
        model = StockAnalysis
        fields = [
            'order_period_start', 'order_period_end', 'status', 'notes'
        ]
    
    def validate(self, data):
        """Validate the analysis period"""
        start_date = data.get('order_period_start')
        end_date = data.get('order_period_end')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError("order_period_start must be before order_period_end")
            
            # Validate that start is Monday and end is Thursday
            if start_date.weekday() != 0:  # Monday = 0
                raise serializers.ValidationError("order_period_start must be a Monday")
            
            if end_date.weekday() != 3:  # Thursday = 3
                raise serializers.ValidationError("order_period_end must be a Thursday")
        
        return data


# Market Price and Procurement Intelligence Serializers

class MarketPriceSerializer(serializers.ModelSerializer):
    """Serializer for market price tracking"""
    
    matched_product_name = serializers.CharField(source='matched_product.name', read_only=True)
    vat_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = MarketPrice
        fields = [
            'id', 'supplier_name', 'invoice_date', 'invoice_reference',
            'product_name', 'matched_product', 'matched_product_name',
            'unit_price_excl_vat', 'vat_amount', 'unit_price_incl_vat',
            'quantity_unit', 'vat_percentage', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'vat_percentage']


class MarketPriceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating market price records"""
    
    class Meta:
        model = MarketPrice
        fields = [
            'supplier_name', 'invoice_date', 'invoice_reference',
            'product_name', 'matched_product', 'unit_price_excl_vat',
            'vat_amount', 'unit_price_incl_vat', 'quantity_unit', 'is_active'
        ]
    
    def validate(self, data):
        """Validate pricing data"""
        excl_vat = data.get('unit_price_excl_vat')
        vat_amount = data.get('vat_amount')
        incl_vat = data.get('unit_price_incl_vat')
        
        if excl_vat and vat_amount and incl_vat:
            expected_incl_vat = excl_vat + vat_amount
            if abs(incl_vat - expected_incl_vat) > 0.01:  # Allow for rounding differences
                raise serializers.ValidationError(
                    f"unit_price_incl_vat ({incl_vat}) should equal unit_price_excl_vat + vat_amount ({expected_incl_vat})"
                )
        
        return data


class ProcurementRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for procurement recommendations"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    recommended_supplier_name = serializers.CharField(source='recommended_supplier.name', read_only=True)
    stock_analysis_period = serializers.SerializerMethodField()
    days_until_recommended_order = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ProcurementRecommendation
        fields = [
            'id', 'stock_analysis', 'product', 'product_name', 'product_department',
            'recommended_quantity', 'recommended_supplier', 'recommended_supplier_name',
            'current_market_price', 'average_market_price_30d', 'price_trend',
            'urgency_level', 'recommended_order_date', 'expected_delivery_date',
            'estimated_total_cost', 'potential_savings', 'status',
            'stock_analysis_period', 'days_until_recommended_order', 'is_overdue',
            'created_at', 'updated_at', 'created_by', 'notes'
        ]
        read_only_fields = [
            'estimated_total_cost', 'days_until_recommended_order', 'is_overdue',
            'created_at', 'updated_at'
        ]
    
    def get_stock_analysis_period(self, obj):
        """Get the analysis period for context"""
        return f"{obj.stock_analysis.order_period_start} to {obj.stock_analysis.order_period_end}"


class ProcurementRecommendationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating procurement recommendations"""
    
    class Meta:
        model = ProcurementRecommendation
        fields = [
            'stock_analysis', 'product', 'recommended_quantity', 'recommended_supplier',
            'current_market_price', 'average_market_price_30d', 'price_trend',
            'urgency_level', 'recommended_order_date', 'expected_delivery_date',
            'potential_savings', 'notes'
        ]
    
    def validate_recommended_order_date(self, value):
        """Validate that recommended order date is not in the past"""
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError("Recommended order date cannot be in the past")
        return value


class ProcurementRecommendationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing procurement recommendations"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    recommended_supplier_name = serializers.CharField(source='recommended_supplier.name', read_only=True)
    days_until_recommended_order = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ProcurementRecommendation
        fields = [
            'id', 'product_name', 'recommended_quantity', 'recommended_supplier_name',
            'urgency_level', 'recommended_order_date', 'estimated_total_cost',
            'status', 'days_until_recommended_order', 'is_overdue'
        ]


class PriceAlertSerializer(serializers.ModelSerializer):
    """Serializer for price alerts"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    
    class Meta:
        model = PriceAlert
        fields = [
            'id', 'product', 'product_name', 'product_department',
            'alert_type', 'threshold_percentage', 'baseline_price',
            'current_price', 'price_change_percentage', 'alert_triggered_at',
            'is_acknowledged', 'acknowledged_by', 'acknowledged_by_name',
            'acknowledged_at', 'recommended_action'
        ]
        read_only_fields = [
            'alert_triggered_at', 'acknowledged_at', 'price_change_percentage'
        ]


class PriceAlertCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating price alerts"""
    
    class Meta:
        model = PriceAlert
        fields = [
            'product', 'alert_type', 'threshold_percentage',
            'baseline_price', 'current_price', 'recommended_action'
        ]
    
    def validate(self, data):
        """Calculate price change percentage"""
        baseline = data.get('baseline_price')
        current = data.get('current_price')
        
        if baseline and current and baseline > 0:
            price_change = ((current - baseline) / baseline) * 100
            data['price_change_percentage'] = price_change
        
        return data


# Enhanced Stock Analysis Serializers with Procurement Integration

class StockAnalysisWithProcurementSerializer(StockAnalysisDetailSerializer):
    """Enhanced stock analysis serializer with procurement recommendations"""
    
    procurement_recommendations = ProcurementRecommendationSerializer(many=True, read_only=True)
    total_procurement_cost = serializers.SerializerMethodField()
    recommendations_by_urgency = serializers.SerializerMethodField()
    
    class Meta(StockAnalysisDetailSerializer.Meta):
        fields = StockAnalysisDetailSerializer.Meta.fields + [
            'procurement_recommendations', 'total_procurement_cost', 'recommendations_by_urgency'
        ]
    
    def get_total_procurement_cost(self, obj):
        """Calculate total estimated procurement cost"""
        return sum(
            rec.estimated_total_cost for rec in obj.procurement_recommendations.all()
            if rec.estimated_total_cost
        )
    
    def get_recommendations_by_urgency(self, obj):
        """Group recommendations by urgency level"""
        recommendations = obj.procurement_recommendations.all()
        urgency_groups = {}
        
        for rec in recommendations:
            urgency = rec.urgency_level
            if urgency not in urgency_groups:
                urgency_groups[urgency] = []
            urgency_groups[urgency].append({
                'product_name': rec.product.name,
                'recommended_quantity': rec.recommended_quantity,
                'estimated_cost': rec.estimated_total_cost
            })
        
        return urgency_groups


# Dynamic Price Management Serializers

class PricingRuleSerializer(serializers.ModelSerializer):
    """Serializer for pricing rules"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    is_effective_now = serializers.SerializerMethodField()
    
    class Meta:
        model = PricingRule
        fields = [
            'id', 'name', 'description', 'customer_segment',
            'base_markup_percentage', 'volatility_adjustment', 'minimum_margin_percentage',
            'category_adjustments', 'trend_multiplier', 'seasonal_adjustment',
            'is_active', 'effective_from', 'effective_until', 'is_effective_now',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_effective_now']
    
    def get_is_effective_now(self, obj):
        """Check if the rule is currently effective"""
        return obj.is_effective()


class PricingRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating pricing rules"""
    
    class Meta:
        model = PricingRule
        fields = [
            'name', 'description', 'customer_segment', 'base_markup_percentage',
            'volatility_adjustment', 'minimum_margin_percentage', 'category_adjustments',
            'trend_multiplier', 'seasonal_adjustment', 'is_active',
            'effective_from', 'effective_until'
        ]
    
    def validate(self, data):
        """Validate pricing rule data"""
        effective_from = data.get('effective_from')
        effective_until = data.get('effective_until')
        
        if effective_from and effective_until:
            if effective_from >= effective_until:
                raise serializers.ValidationError("effective_from must be before effective_until")
        
        # Validate markup percentages
        base_markup = data.get('base_markup_percentage', 0)
        minimum_margin = data.get('minimum_margin_percentage', 0)
        
        if base_markup < minimum_margin:
            raise serializers.ValidationError(
                "base_markup_percentage should be at least equal to minimum_margin_percentage"
            )
        
        return data


class CustomerPriceListItemSerializer(serializers.ModelSerializer):
    """Serializer for customer price list items"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    margin_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_price_increase = serializers.BooleanField(read_only=True)
    is_significant_change = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CustomerPriceListItem
        fields = [
            'id', 'product', 'product_name', 'product_department',
            'market_price_excl_vat', 'market_price_incl_vat', 'market_price_date',
            'markup_percentage', 'customer_price_excl_vat', 'customer_price_incl_vat',
            'previous_price', 'price_change_percentage', 'margin_amount',
            'unit_of_measure', 'product_category', 'is_volatile', 'is_seasonal',
            'is_premium', 'is_price_increase', 'is_significant_change'
        ]
        read_only_fields = ['margin_amount', 'is_price_increase', 'is_significant_change']


class CustomerPriceListSerializer(serializers.ModelSerializer):
    """Serializer for customer price lists"""
    
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    pricing_rule_name = serializers.CharField(source='pricing_rule.name', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = CustomerPriceList
        fields = [
            'id', 'customer', 'customer_name', 'pricing_rule', 'pricing_rule_name',
            'list_name', 'effective_from', 'effective_until', 'is_current', 'days_until_expiry',
            'based_on_market_data', 'market_data_source', 'total_products',
            'average_markup_percentage', 'total_list_value', 'status',
            'sent_at', 'acknowledged_at', 'generated_at', 'generated_by', 'generated_by_name', 'notes'
        ]
        read_only_fields = ['generated_at', 'is_current', 'days_until_expiry']


class CustomerPriceListDetailSerializer(CustomerPriceListSerializer):
    """Detailed serializer for customer price lists with items"""
    
    items = CustomerPriceListItemSerializer(many=True, read_only=True)
    volatile_items = serializers.SerializerMethodField()
    price_increases = serializers.SerializerMethodField()
    
    class Meta(CustomerPriceListSerializer.Meta):
        fields = CustomerPriceListSerializer.Meta.fields + ['items', 'volatile_items', 'price_increases']
    
    def get_volatile_items(self, obj):
        """Get items with volatile pricing"""
        volatile_items = obj.items.filter(is_volatile=True)
        return CustomerPriceListItemSerializer(volatile_items, many=True).data
    
    def get_price_increases(self, obj):
        """Get items with price increases"""
        price_increases = obj.items.filter(price_change_percentage__gt=0)
        return CustomerPriceListItemSerializer(price_increases, many=True).data


class CustomerPriceListCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating customer price lists"""
    
    class Meta:
        model = CustomerPriceList
        fields = [
            'customer', 'pricing_rule', 'list_name', 'effective_from', 'effective_until',
            'based_on_market_data', 'market_data_source', 'notes'
        ]
    
    def validate(self, data):
        """Validate price list data"""
        effective_from = data.get('effective_from')
        effective_until = data.get('effective_until')
        
        if effective_from and effective_until:
            if effective_from >= effective_until:
                raise serializers.ValidationError("effective_from must be before effective_until")
        
        # Check for overlapping price lists for the same customer
        customer = data.get('customer')
        if customer:
            overlapping = CustomerPriceList.objects.filter(
                customer=customer,
                effective_from__lte=effective_until,
                effective_until__gte=effective_from
            )
            
            if self.instance:
                overlapping = overlapping.exclude(id=self.instance.id)
            
            if overlapping.exists():
                raise serializers.ValidationError(
                    "This customer already has a price list for the specified period"
                )
        
        return data


class WeeklyPriceReportSerializer(serializers.ModelSerializer):
    """Serializer for weekly price reports"""
    
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    week_number = serializers.IntegerField(read_only=True)
    year = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = WeeklyPriceReport
        fields = [
            'id', 'report_name', 'report_week_start', 'report_week_end',
            'week_number', 'year', 'total_market_prices_analyzed',
            'average_market_volatility', 'most_volatile_product', 'most_volatile_percentage',
            'total_price_lists_generated', 'total_customers_affected', 'average_price_increase',
            'total_procurement_recommendations', 'estimated_procurement_cost',
            'potential_savings_identified', 'key_insights', 'status',
            'generated_at', 'generated_by', 'generated_by_name'
        ]
        read_only_fields = ['generated_at', 'week_number', 'year']


class WeeklyPriceReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating weekly price reports"""
    
    class Meta:
        model = WeeklyPriceReport
        fields = [
            'report_name', 'report_week_start', 'report_week_end'
        ]
    
    def validate(self, data):
        """Validate report data"""
        start_date = data.get('report_week_start')
        end_date = data.get('report_week_end')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError("report_week_start must be before report_week_end")
            
            # Validate that it's a Monday to Sunday period
            if start_date.weekday() != 0:  # Monday = 0
                raise serializers.ValidationError("report_week_start must be a Monday")
            
            if end_date.weekday() != 6:  # Sunday = 6
                raise serializers.ValidationError("report_week_end must be a Sunday")
            
            # Check that it's exactly one week
            if (end_date - start_date).days != 6:
                raise serializers.ValidationError("Report period must be exactly one week (Monday to Sunday)")
        
        return data


# Enhanced Market Price Serializers with Customer Pricing Integration

class MarketPriceWithCustomerImpactSerializer(MarketPriceSerializer):
    """Enhanced market price serializer showing customer pricing impact"""
    
    affected_customers = serializers.SerializerMethodField()
    price_volatility_level = serializers.SerializerMethodField()
    
    class Meta(MarketPriceSerializer.Meta):
        fields = MarketPriceSerializer.Meta.fields + ['affected_customers', 'price_volatility_level']
    
    def get_affected_customers(self, obj):
        """Get customers affected by this price"""
        if obj.matched_product:
            price_list_items = CustomerPriceListItem.objects.filter(
                product=obj.matched_product,
                price_list__status='active'
            ).select_related('price_list__customer')
            
            return [
                {
                    'customer_name': item.price_list.customer.get_full_name(),
                    'current_price': item.customer_price_incl_vat,
                    'markup_percentage': item.markup_percentage
                }
                for item in price_list_items
            ]
        return []
    
    def get_price_volatility_level(self, obj):
        """Calculate price volatility level for this product"""
        if obj.matched_product:
            # Get recent prices for volatility calculation
            from datetime import date, timedelta
            thirty_days_ago = date.today() - timedelta(days=30)
            
            recent_prices = MarketPrice.objects.filter(
                matched_product=obj.matched_product,
                invoice_date__gte=thirty_days_ago,
                is_active=True
            ).values_list('unit_price_incl_vat', flat=True)
            
            if len(recent_prices) > 1:
                prices = list(recent_prices)
                min_price = min(prices)
                max_price = max(prices)
                
                if min_price > 0:
                    volatility = ((max_price - min_price) / min_price) * 100
                    
                    if volatility > 50:
                        return 'extremely_volatile'
                    elif volatility > 25:
                        return 'highly_volatile'
                    elif volatility > 10:
                        return 'volatile'
                    else:
                        return 'stable'
        
        return 'unknown'
