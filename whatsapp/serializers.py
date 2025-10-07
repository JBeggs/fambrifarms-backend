"""
Serializers for WhatsApp message corrections and reprocessing
"""

from rest_framework import serializers
from .models import WhatsAppMessage, StockUpdate, MessageProcessingLog


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    """Serializer for WhatsApp messages"""
    class Meta:
        model = WhatsAppMessage
        fields = '__all__'


class StockUpdateSerializer(serializers.ModelSerializer):
    """Serializer for stock updates"""
    class Meta:
        model = StockUpdate
        fields = '__all__'


class MessageProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for message processing logs"""
    class Meta:
        model = MessageProcessingLog
        fields = '__all__'


class MessageBatchSerializer(serializers.Serializer):
    """Serializer for batch message processing"""
    messages = serializers.ListField(child=serializers.DictField())


class ProcessMessagesSerializer(serializers.Serializer):
    """Serializer for processing messages to orders"""
    message_ids = serializers.ListField(child=serializers.CharField())


class EditMessageSerializer(serializers.Serializer):
    """Serializer for editing message content"""
    message_id = serializers.CharField(max_length=255)
    edited_content = serializers.CharField()
    processed = serializers.BooleanField(required=False)


class UpdateMessageTypeSerializer(serializers.Serializer):
    """Serializer for updating message type"""
    message_id = serializers.CharField(max_length=255)
    message_type = serializers.CharField(max_length=20)


class OrderCreationResultSerializer(serializers.Serializer):
    """Serializer for order creation results"""
    status = serializers.CharField()
    orders_created = serializers.IntegerField()
    errors = serializers.ListField(required=False)
    warnings = serializers.ListField(required=False)


class StockValidationSerializer(serializers.Serializer):
    """Serializer for stock validation results"""
    valid = serializers.BooleanField()
    issues = serializers.ListField(required=False)
    recommendations = serializers.ListField(required=False)


class MessageCorrectionSerializer(serializers.Serializer):
    """Serializer for message corrections"""
    message_id = serializers.CharField(max_length=255)
    corrections = serializers.DictField()
    
    def validate_message_id(self, value):
        """Validate that the message exists"""
        try:
            WhatsAppMessage.objects.get(message_id=value)
            return value
        except WhatsAppMessage.DoesNotExist:
            raise serializers.ValidationError("Message not found")


class MessageReprocessSerializer(serializers.Serializer):
    """Serializer for message reprocessing"""
    message_id = serializers.CharField(max_length=255)
    
    def validate_message_id(self, value):
        """Validate that the message exists"""
        try:
            WhatsAppMessage.objects.get(message_id=value)
            return value
        except WhatsAppMessage.DoesNotExist:
            raise serializers.ValidationError("Message not found")