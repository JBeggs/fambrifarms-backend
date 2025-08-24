from rest_framework import serializers
from .models import Supplier, SupplierProduct


class SupplierListSerializer(serializers.ModelSerializer):
    """Simplified serializer for supplier lists"""
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_name', 'contact_email', 'contact_phone',
            'city', 'is_active', 'products_count'
        ]
    
    def get_products_count(self, obj):
        return obj.products.count()


class SupplierDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual suppliers"""
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Supplier
        fields = '__all__'
        read_only_fields = ['id']
    
    def get_products_count(self, obj):
        return obj.products.count()


class SupplierProductListSerializer(serializers.ModelSerializer):
    """Simplified serializer for supplier product lists"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    
    class Meta:
        model = SupplierProduct
        fields = [
            'id', 'supplier', 'supplier_name', 'product', 'product_name',
            'product_department', 'supplier_price', 'stock_quantity',
            'is_available'
        ]


class SupplierProductDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual supplier products"""
    supplier_detail = SupplierListSerializer(source='supplier', read_only=True)
    product_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = SupplierProduct
        fields = '__all__'
        read_only_fields = ['id']
    
    def get_product_detail(self, obj):
        from products.serializers import ProductSerializer
        return ProductSerializer(obj.product).data


class SupplierStockUpdateSerializer(serializers.Serializer):
    """For updating supplier stock quantities"""
    supplier_product_id = serializers.IntegerField()
    new_stock_quantity = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(max_length=500, required=False)
