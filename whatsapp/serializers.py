from rest_framework import serializers
from .models import WhatsAppMessage, SalesRep, PurchaseOrder, POItem

class WhatsAppMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppMessage
        fields = [
            'id', 'message_id', 'sender_phone', 'sender_name', 'message_text',
            'processed', 'processing_error', 'parsed_items', 'parsing_confidence',
            'parsing_method', 'order', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']

class SalesRepSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesRep
        fields = [
            'id', 'name', 'phone_number', 'whatsapp_number', 'is_active',
            'specialties', 'average_response_time', 'total_orders_handled',
            'response_rate', 'preferred_contact_hours_start', 'preferred_contact_hours_end',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class POItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = POItem
        fields = [
            'id', 'product_name', 'quantity_requested', 'unit',
            'quantity_confirmed', 'price_per_unit', 'total_price',
            'confirmed', 'notes'
        ]

class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = POItemSerializer(many=True, read_only=True)
    sales_rep_name = serializers.CharField(source='sales_rep.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'order', 'order_number', 'sales_rep', 'sales_rep_name',
            'status', 'whatsapp_message_sent', 'whatsapp_response',
            'estimated_total', 'confirmed_total', 'delivery_date',
            'created_at', 'sent_at', 'confirmed_at', 'items'
        ]
        read_only_fields = ['id', 'po_number', 'created_at', 'sent_at', 'confirmed_at']
