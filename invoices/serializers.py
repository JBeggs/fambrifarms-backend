from rest_framework import serializers
from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'restaurant', 'order',
            'issue_date', 'due_date', 'subtotal', 'tax_amount',
            'total_amount', 'status', 'created_at'
        ]
        read_only_fields = ['invoice_number', 'issue_date', 'tax_amount', 'total_amount', 'created_at']

