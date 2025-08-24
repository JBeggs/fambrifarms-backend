from rest_framework import serializers
from .models import SupplierPurchaseOrder, SupplierPOItem

class SupplierPOItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = SupplierPOItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'received_quantity', 'order_item']

class SupplierPOSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    items = SupplierPOItemSerializer(many=True, read_only=True)

    class Meta:
        model = SupplierPurchaseOrder
        fields = ['id', 'supplier', 'supplier_name', 'order', 'status', 'expected_date', 'notes', 'items', 'created_at', 'updated_at']
