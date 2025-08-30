from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class WhatsAppMessage(models.Model):
    """Store WhatsApp messages for processing"""
    message_id = models.CharField(max_length=100, unique=True)
    sender_phone = models.CharField(max_length=20)
    sender_name = models.CharField(max_length=100)
    message_text = models.TextField()
    
    # Processing status
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    
    # AI parsing results
    parsed_items = models.JSONField(null=True, blank=True)
    parsing_confidence = models.FloatField(default=0.0)
    parsing_method = models.CharField(max_length=50, default='manual')  # 'manual', 'claude', 'openai'
    
    # Links to created order
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"WhatsApp from {self.sender_name}: {self.message_text[:50]}..."

class SalesRep(models.Model):
    """Sales representatives at Pretoria Market"""
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    whatsapp_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    
    # Specialties - which products they handle best
    specialties = models.JSONField(default=list, blank=True)  # ["vegetables", "herbs", "fruits"]
    
    # Performance tracking
    average_response_time = models.DurationField(null=True, blank=True)
    total_orders_handled = models.IntegerField(default=0)
    response_rate = models.FloatField(default=0.0)  # Percentage of orders they respond to
    
    # Contact preferences
    preferred_contact_hours_start = models.TimeField(default='07:00')
    preferred_contact_hours_end = models.TimeField(default='17:00')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.whatsapp_number})"

class PurchaseOrder(models.Model):
    """Purchase orders sent to sales reps"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Sales Rep'),
        ('confirmed', 'Confirmed by Sales Rep'),
        ('partially_confirmed', 'Partially Confirmed'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    po_number = models.CharField(max_length=20, unique=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='purchase_orders')
    sales_rep = models.ForeignKey(SalesRep, on_delete=models.CASCADE, related_name='purchase_orders')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # WhatsApp communication
    whatsapp_message_sent = models.TextField(blank=True)  # The PO message sent
    whatsapp_response = models.TextField(blank=True)  # Sales rep response
    
    # Pricing and delivery
    estimated_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    confirmed_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            import random
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = str(random.randint(100, 999))
            self.po_number = f"PO{date_str}{random_str}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PO {self.po_number} - {self.sales_rep.name}"

class POItem(models.Model):
    """Items in a purchase order"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=200)  # Product name as text (not FK for flexibility)
    quantity_requested = models.DecimalField(max_digits=8, decimal_places=2)
    unit = models.CharField(max_length=20)
    
    # Sales rep response
    quantity_confirmed = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status and notes
    confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)  # Sales rep notes about availability, quality, etc.
    
    def __str__(self):
        return f"{self.product_name} x{self.quantity_requested}{self.unit}"