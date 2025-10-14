from rest_framework import serializers
from .models import Product, Department, ProductAlert, Recipe, MarketProcurementRecommendation, MarketProcurementItem

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'is_active', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    alert_count = serializers.SerializerMethodField()
    stock_level = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'department', 'department_name',
            'price', 'unit', 'stock_level', 'minimum_stock', 'is_active',
            'needs_setup', 'alert_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['stock_level']  # Prevent direct stock level updates
    
    def get_alert_count(self, obj):
        return obj.alerts.filter(is_resolved=False).count()
    
    def validate(self, data):
        """Prevent stock_level updates through API"""
        if 'stock_level' in data:
            raise serializers.ValidationError({
                'stock_level': 'Stock levels can only be updated through inventory management or WhatsApp stock updates.'
            })
        return data

class ProductAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ProductAlert
        fields = [
            'id', 'product', 'product_name', 'alert_type', 'message',
            'is_resolved', 'created_by_order', 'created_at', 'resolved_at'
        ]

class RecipeSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = Recipe
        fields = [
            'id', 'product', 'product_name', 'ingredients', 'instructions',
            'prep_time_minutes', 'yield_quantity', 'yield_unit',
            'created_at', 'updated_at'
        ]

class MarketProcurementItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    supplier_name = serializers.CharField(source='preferred_supplier.name', read_only=True)
    supplier_id = serializers.IntegerField(source='preferred_supplier.id', read_only=True)
    
    class Meta:
        model = MarketProcurementItem
        fields = [
            'id', 'product', 'product_name', 'unit', 'priority', 'reasoning',
            'needed_quantity', 'recommended_quantity', 'estimated_unit_price',
            'estimated_total_cost', 'supplier_name', 'supplier_id',
            'preferred_supplier', 'supplier_product', 'procurement_method'
        ]

class MarketProcurementRecommendationSerializer(serializers.ModelSerializer):
    items = MarketProcurementItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = MarketProcurementRecommendation
        fields = [
            'id', 'for_date', 'status', 'total_estimated_cost',
            'created_at', 'approved_at', 'approved_by', 'items'
        ]