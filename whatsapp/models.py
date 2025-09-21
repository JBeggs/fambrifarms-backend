from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import re
from .message_parser import django_message_parser

User = get_user_model()

class WhatsAppMessage(models.Model):
    """WhatsApp messages scraped from the ORDERS Restaurants group"""
    
    MESSAGE_TYPES = [
        ('order', 'Customer Order'),
        ('stock', 'Stock Update'),
        ('instruction', 'Instruction/Note'),
        ('demarcation', 'Order Day Demarcation'),
        ('image', 'Image Message'),
        ('voice', 'Voice Message'),
        ('video', 'Video Message'),
        ('document', 'Document Message'),
        ('sticker', 'Sticker Message'),
        ('other', 'Other'),
    ]
    
    # Message identification
    message_id = models.CharField(max_length=100, unique=True)
    chat_name = models.CharField(max_length=200)
    sender_name = models.CharField(max_length=200)
    sender_phone = models.CharField(max_length=20, blank=True)
    
    # Message content
    content = models.TextField()
    cleaned_content = models.TextField(blank=True)
    content_hash = models.CharField(max_length=32, blank=True, help_text="MD5 hash of content for deduplication")
    timestamp = models.DateTimeField()
    scraped_at = models.DateTimeField(auto_now_add=True)
    
    # Media content
    media_url = models.URLField(blank=True, null=True, help_text="URL for image/video/document")
    media_type = models.CharField(max_length=20, blank=True, help_text="Type of media: image, voice, video, document, sticker")
    media_info = models.TextField(blank=True, help_text="Additional media info like voice duration, file size, etc.")
    
    # Message context
    is_forwarded = models.BooleanField(default=False)
    forwarded_info = models.TextField(blank=True, help_text="Info about forwarded message source")
    is_reply = models.BooleanField(default=False)
    reply_content = models.TextField(blank=True, help_text="Content of message being replied to")
    
    # Classification
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='other')
    confidence_score = models.FloatField(default=0.0)
    
    # Processing status
    processed = models.BooleanField(default=False)
    order = models.ForeignKey('orders.Order', null=True, blank=True, on_delete=models.SET_NULL)
    # Soft delete flag
    is_deleted = models.BooleanField(default=False)
    
    # Parsed data
    parsed_items = models.JSONField(default=list)
    instructions = models.TextField(blank=True)
    
    # Manual editing
    edited = models.BooleanField(default=False)
    original_content = models.TextField(blank=True)
    manual_company = models.CharField(max_length=200, blank=True, null=True, help_text="Manually selected company name")
    
    # Order day context
    order_day = models.CharField(max_length=10, blank=True)  # Monday/Thursday
    
    # HTML processing and expansion tracking (for simplified architecture)
    raw_html = models.TextField(blank=True, help_text="Raw HTML from WhatsApp message element")
    was_expanded = models.BooleanField(default=False, help_text="Whether message was expanded from truncated state")
    expansion_failed = models.BooleanField(default=False, help_text="Whether expansion was attempted but failed")
    original_preview = models.TextField(blank=True, help_text="Preview text before expansion")
    needs_manual_review = models.BooleanField(default=False, help_text="Flagged for manual review")
    review_reason = models.CharField(max_length=255, blank=True, help_text="Reason for manual review")
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['message_type', 'processed']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['sender_phone']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.sender_name}: {self.content[:50]}..."
    
    def is_stock_controller(self):
        """Check if message is from SHALLOME (stock controller)"""
        return ('+27 61 674 9368' in self.sender_phone or 
                'SHALLOME' in self.sender_name.upper() or
                self.content.upper().startswith('SHALLOME') or
                '+27 61 674 9368' in self.content)
    
    def is_order_day_demarcation(self):
        """Check if message marks start of order day"""
        content_upper = self.content.upper()
        return ('ORDERS STARTS HERE' in content_upper or 
                '👇👇👇' in content_upper or
                'THURSDAY ORDERS STARTS HERE' in content_upper or
                'TUESDAY ORDERS STARTS HERE' in content_upper)
    
    def extract_company_name(self):
        """Extract company name from message using enhanced MessageParser"""
        # CRITICAL FIX: Don't extract company names from stock messages
        # SHALLOME should never be treated as a customer
        if self.message_type == 'stock' or self.is_stock_controller():
            return ''
            
        # Prioritize manual company selection
        if self.manual_company:
            return self.manual_company
            
        company = django_message_parser.to_canonical_company(self.content)
        
        # CRITICAL FIX: Don't treat SHALLOME as a customer even if found in content
        if company and company.upper() == 'SHALLOME':
            return ''
        
        # If no company found in current message, look at recent previous messages
        if not company and self.message_type == 'order':
            company = self._extract_company_from_context()
        
        # CRITICAL FIX: ALWAYS set manual_company when we find a company
        # This preserves the assignment even if the message content is edited
        if company and not self.manual_company:
            self.manual_company = company
            self.save(update_fields=['manual_company'])
        
        return company or ''
    
    def _extract_company_from_context(self):
        """Look at nearby messages for company context - check ONLY one message before and one message after"""
        
        # Get exactly one message before and one message after this message
        # Order by timestamp and ID to ensure consistent ordering
        all_messages = WhatsAppMessage.objects.filter(
            chat_name=self.chat_name,
            is_deleted=False
        ).exclude(
            id=self.id  # Exclude current message
        ).order_by('timestamp', 'id')
        
        # Find the position of current message
        current_message_time = self.timestamp
        
        # Get one message immediately before (closest timestamp before current)
        message_before = all_messages.filter(
            timestamp__lt=current_message_time
        ).last()  # Last = most recent before current
        
        # Get one message immediately after (closest timestamp after current)  
        message_after = all_messages.filter(
            timestamp__gt=current_message_time
        ).first()  # First = earliest after current
        
        # Check the message immediately after first (company names often come after order items)
        if message_after:
            company = django_message_parser.to_canonical_company(message_after.content)
            if company:
                print(f"[CONTEXT] Found company '{company}' in message AFTER (ID: {message_after.id})")
                return company
        
        # Then check the message immediately before
        if message_before:
            company = django_message_parser.to_canonical_company(message_before.content)
            if company:
                print(f"[CONTEXT] Found company '{company}' in message BEFORE (ID: {message_before.id})")
                return company
        
        print(f"[CONTEXT] No company found in immediate context for message {self.id}")
        return None
    
    def extract_order_items(self):
        """Extract order items from message using enhanced MessageParser"""
        return django_message_parser.extract_order_items(self.content)
    
    def extract_instructions(self):
        """Extract instructions from message using enhanced MessageParser"""
        return django_message_parser.extract_instructions(self.content)


class StockUpdate(models.Model):
    """Stock updates from SHALLOME (+27 61 674 9368)"""
    
    message = models.OneToOneField(WhatsAppMessage, on_delete=models.CASCADE)
    stock_date = models.DateField()
    order_day = models.CharField(max_length=10)  # Monday/Thursday
    
    # Stock items: {product_name: {quantity: X, unit: 'kg'}}
    items = models.JSONField(default=dict)
    
    # Processing
    processed = models.BooleanField(default=False)
    applied_to_orders = models.ManyToManyField('orders.Order', blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-stock_date']
        indexes = [
            models.Index(fields=['order_day', 'processed']),
            models.Index(fields=['stock_date']),
        ]
    
    def __str__(self):
        return f"Stock Update {self.stock_date} ({self.order_day}) - {len(self.items)} items"
    
    def get_available_quantity(self, product_name):
        """Get available quantity for a product"""
        product_key = product_name.lower().strip()
        for key, data in self.items.items():
            if key.lower().strip() == product_key:
                return data.get('quantity', 0)
        return 0
    
    def get_product_unit(self, product_name):
        """Get unit for a product"""
        product_key = product_name.lower().strip()
        for key, data in self.items.items():
            if key.lower().strip() == product_key:
                return data.get('unit', '')
        return ''
    
    def deduct_stock(self, product_name, quantity):
        """Deduct quantity from available stock"""
        product_key = None
        for key in self.items.keys():
            if key.lower().strip() == product_name.lower().strip():
                product_key = key
                break
        
        if product_key and self.items[product_key]['quantity'] >= quantity:
            self.items[product_key]['quantity'] -= quantity
            self.save()
            return True
        return False


class OrderDayDemarcation(models.Model):
    """Marks the start of order collection for a specific day"""
    
    message = models.OneToOneField(WhatsAppMessage, on_delete=models.CASCADE)
    order_day = models.CharField(max_length=10)  # Monday/Thursday
    demarcation_date = models.DateField()
    
    # Context
    active = models.BooleanField(default=True)
    orders_collected = models.ManyToManyField('orders.Order', blank=True)
    
    class Meta:
        ordering = ['-demarcation_date']
        unique_together = ['order_day', 'demarcation_date']
    
    def __str__(self):
        return f"{self.order_day} orders - {self.demarcation_date}"


class MessageProcessingLog(models.Model):
    """Log of message processing activities"""
    
    ACTIONS = [
        ('classified', 'Message Classified'),
        ('parsed', 'Items Parsed'),
        ('order_created', 'Order Created'),
        ('stock_updated', 'Stock Updated'),
        ('edited', 'Message Edited'),
        ('error', 'Processing Error'),
    ]
    
    message = models.ForeignKey(WhatsAppMessage, on_delete=models.CASCADE, related_name='processing_logs')
    action = models.CharField(max_length=20, choices=ACTIONS)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    stack_trace = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.message.sender_name} - {self.action} - {self.timestamp}"
