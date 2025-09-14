from rest_framework import serializers
from .models import WhatsAppMessage, StockUpdate, OrderDayDemarcation, MessageProcessingLog
from orders.serializers import OrderSerializer

class WhatsAppMessageSerializer(serializers.ModelSerializer):
    """Serializer for WhatsApp messages"""
    
    order_details = OrderSerializer(source='order', read_only=True)
    company_name = serializers.SerializerMethodField()
    parsed_items = serializers.SerializerMethodField()
    instructions = serializers.SerializerMethodField()
    is_stock_controller = serializers.SerializerMethodField()

    # CamelCase aliases expected by the Flutter client
    cleanedContent = serializers.CharField(source='cleaned_content', read_only=True)
    mediaInfo = serializers.CharField(source='media_info', read_only=True)
    
    class Meta:
        model = WhatsAppMessage
        fields = [
            'id', 'message_id', 'chat_name', 'sender_name', 'sender_phone',
            'content', 'cleaned_content', 'cleanedContent', 'timestamp', 'scraped_at',
            'message_type', 'confidence_score', 'processed', 'order_details',
            'parsed_items', 'instructions', 'edited', 'original_content', 'manual_company',
            'order_day', 'company_name', 'is_stock_controller',
            # Media fields
            'media_url', 'media_type', 'media_info', 'mediaInfo',
            # Context fields  ß
            'is_forwarded', 'forwarded_info', 'is_reply', 'reply_content'
        ]
        read_only_fields = ['scraped_at', 'message_id']
    
    def get_company_name(self, obj):
        """Extract company name from message"""
        return obj.extract_company_name()
    
    def get_parsed_items(self, obj):
        """Extract parsed order items from message"""
        if obj.message_type == 'order':
            return obj.extract_order_items()
        return []
    
    def get_instructions(self, obj):
        """Extract instructions from message"""
        instructions = obj.extract_instructions()
        return '\n'.join(instructions) if instructions else ""
    
    def get_is_stock_controller(self, obj):
        """Check if message is from stock controller"""
        return obj.is_stock_controller()


class StockUpdateSerializer(serializers.ModelSerializer):
    """Serializer for stock updates"""
    
    message_details = WhatsAppMessageSerializer(source='message', read_only=True)
    total_items = serializers.SerializerMethodField()
    
    class Meta:
        model = StockUpdate
        fields = [
            'id', 'stock_date', 'order_day', 'items', 'processed',
            'created_at', 'updated_at', 'message_details', 'total_items'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_items(self, obj):
        """Get total number of items in stock"""
        return len(obj.items)


class OrderDayDemarcationSerializer(serializers.ModelSerializer):
    """Serializer for order day demarcations"""
    
    message_details = WhatsAppMessageSerializer(source='message', read_only=True)
    orders_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderDayDemarcation
        fields = [
            'id', 'order_day', 'demarcation_date', 'active',
            'message_details', 'orders_count'
        ]
    
    def get_orders_count(self, obj):
        """Get number of orders collected for this day"""
        return obj.orders_collected.count()


class MessageProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for message processing logs"""
    
    class Meta:
        model = MessageProcessingLog
        fields = [
            'id', 'action', 'details', 'timestamp',
            'error_message', 'stack_trace'
        ]
        read_only_fields = ['timestamp']


class MessageBatchSerializer(serializers.Serializer):
    """Serializer for batch message processing"""
    
    messages = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of message objects from WhatsApp scraper"
    )
    
    def validate_messages(self, value):
        """Validate message format"""
        required_fields = ['id', 'chat', 'sender', 'content', 'timestamp']
        
        for msg in value:
            for field in required_fields:
                if field not in msg:
                    raise serializers.ValidationError(
                        f"Missing required field '{field}' in message"
                    )
        
        return value


class ProcessMessagesSerializer(serializers.Serializer):
    """Serializer for processing messages to orders"""
    
    message_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of message IDs to process into orders"
    )
    
    def validate_message_ids(self, value):
        """Validate that all message IDs exist"""
        existing_ids = WhatsAppMessage.objects.filter(
            message_id__in=value
        ).values_list('message_id', flat=True)
        
        missing_ids = set(value) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError(
                f"Message IDs not found: {list(missing_ids)}"
            )
        
        return value


class EditMessageSerializer(serializers.Serializer):
    """Serializer for editing message content"""
    
    message_id = serializers.CharField(help_text="ID of message to edit")
    edited_content = serializers.CharField(help_text="New content for the message")
    
    def validate_message_id(self, value):
        """Validate that message exists"""
        if not WhatsAppMessage.objects.filter(message_id=value).exists():
            raise serializers.ValidationError("Message not found")
        return value


class StockValidationSerializer(serializers.Serializer):
    """Serializer for stock validation results"""
    
    order_id = serializers.IntegerField()
    validation_status = serializers.CharField()
    items = serializers.ListField(
        child=serializers.DictField()
    )
    stock_update_date = serializers.DateField(allow_null=True)
    total_requested = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_allocated = serializers.DecimalField(max_digits=10, decimal_places=2)
    allocation_percentage = serializers.FloatField()


class OrderCreationResultSerializer(serializers.Serializer):
    """Serializer for order creation results"""
    
    status = serializers.CharField()
    orders_created = serializers.IntegerField()
    order_numbers = serializers.ListField(child=serializers.CharField())
    errors = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    warnings = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
