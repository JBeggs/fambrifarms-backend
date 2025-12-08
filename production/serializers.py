from rest_framework import serializers
from .models import Recipe, RecipeIngredient
from products.models import Product


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Serializer for recipe ingredients"""
    raw_material_id = serializers.IntegerField(source='raw_material.id', read_only=True)
    raw_material_name = serializers.CharField(source='raw_material.name', read_only=True)
    raw_material_unit = serializers.CharField(source='raw_material.unit', read_only=True)
    
    class Meta:
        model = RecipeIngredient
        fields = [
            'id',
            'raw_material',  # Product ID
            'raw_material_id',
            'raw_material_name',
            'raw_material_unit',
            'quantity',
            'unit',
            'weight_kg',
            'preparation_notes',
            'is_optional',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipes with ingredients"""
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    ingredients = RecipeIngredientSerializer(many=True, read_only=True)
    
    class Meta:
        model = Recipe
        fields = [
            'id',
            'product',  # Product ID
            'product_id',
            'product_name',
            'name',
            'description',
            'batch_size',
            'production_time_minutes',
            'yield_percentage',
            'is_active',
            'version',
            'ingredients',  # Nested ingredients
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

