from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import (
    UnitOfMeasure, RawMaterial, RawMaterialBatch, ProductionRecipe, 
    RecipeIngredient, FinishedInventory, StockMovement, ProductionBatch, 
    StockAlert
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
