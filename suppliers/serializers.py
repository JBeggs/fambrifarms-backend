from rest_framework import serializers
from .models import Supplier, SalesRep, SupplierProduct

class SalesRepSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesRep
        fields = ['id', 'name', 'email', 'phone', 'position', 'is_active', 'is_primary']

class SupplierSerializer(serializers.ModelSerializer):
    sales_reps = SalesRepSerializer(many=True, read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone', 'address',
            'registration_number', 'tax_number', 'is_active', 'payment_terms_days',
            'lead_time_days', 'minimum_order_value', 'sales_reps'
        ]

class SupplierProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = SupplierProduct
        fields = [
            'id', 'supplier', 'supplier_name', 'product', 'product_name',
            'supplier_product_code', 'supplier_product_name', 'supplier_price',
            'currency', 'is_available', 'stock_quantity', 'minimum_order_quantity',
            'lead_time_days', 'quality_rating', 'last_order_date'
        ]
