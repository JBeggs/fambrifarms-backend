from rest_framework import serializers
from .models import Product, Department, ProductAlert, Recipe

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'is_active', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    alert_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'department', 'department_name',
            'price', 'unit', 'stock_level', 'minimum_stock', 'is_active',
            'needs_setup', 'alert_count', 'created_at', 'updated_at'
        ]
    
    def get_alert_count(self, obj):
        return obj.alerts.filter(is_resolved=False).count()

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