from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import random
from datetime import date, timedelta

User = get_user_model()

def validate_order_date(order_date):
    """Validate that order is placed on Monday or Thursday only"""
    if order_date.weekday() not in settings.ORDER_DAYS:
        raise ValidationError(
            f'Orders can only be placed on Monday and Thursday. '
            f'You selected {order_date.strftime("%A")}.'
        )

def validate_delivery_date(delivery_date):
    """Validate that delivery is scheduled for Tuesday, Wednesday, or Friday only"""
    if delivery_date.weekday() not in settings.DELIVERY_DAYS:
        raise ValidationError(
            f'Deliveries can only be scheduled for Tuesday, Wednesday, and Friday. '
            f'You selected {delivery_date.strftime("%A")}.'
        )

def calculate_delivery_date(order_date):
    """Auto-calculate delivery date based on order date"""
    if order_date.weekday() == 0:  # Monday
        # Monday orders can be delivered Tuesday or Wednesday
        return order_date + timedelta(days=1)  # Default to Tuesday
    elif order_date.weekday() == 3:  # Thursday
        # Thursday orders delivered Friday
        return order_date + timedelta(days=1)  # Friday
    else:
        raise ValidationError("Orders can only be placed on Monday or Thursday")

class Order(models.Model):
    STATUS_CHOICES = [
        ('received', 'Received via WhatsApp'),
        ('parsed', 'AI Parsed'),
        ('confirmed', 'Manager Confirmed'),
        ('po_sent', 'PO Sent to Sales Rep'),
        ('po_confirmed', 'Sales Rep Confirmed'),
        ('delivered', 'Delivered to Customer'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic order info
    restaurant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    
    # Scheduling (CRITICAL - Monday/Thursday → Tuesday/Wednesday/Friday)
    order_date = models.DateField(validators=[validate_order_date])
    delivery_date = models.DateField(validators=[validate_delivery_date])
    
    # WhatsApp integration
    whatsapp_message_id = models.CharField(max_length=100, null=True, blank=True)
    original_message = models.TextField(blank=True)
    parsed_by_ai = models.BooleanField(null=True, blank=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-generate order number
        if not self.order_number:
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = str(random.randint(1000, 9999))
            self.order_number = f"FB{date_str}{random_str}"
        
        # Auto-calculate delivery date if not set
        if not self.delivery_date and self.order_date:
            self.delivery_date = calculate_delivery_date(self.order_date)
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate business rules"""
        super().clean()
        
        # Validate order date is Monday or Thursday
        if self.order_date:
            validate_order_date(self.order_date)
        
        # Validate delivery date is Tuesday, Wednesday, or Friday
        if self.delivery_date:
            validate_delivery_date(self.delivery_date)
        
        # Validate delivery date makes sense for order date
        if self.order_date and self.delivery_date:
            expected_delivery = calculate_delivery_date(self.order_date)
            if self.order_date.weekday() == 0:  # Monday
                # Monday orders can be delivered Tue or Wed
                if self.delivery_date.weekday() not in [1, 2]:
                    raise ValidationError(
                        'Monday orders can only be delivered on Tuesday or Wednesday.'
                    )
            elif self.order_date.weekday() == 3:  # Thursday
                # Thursday orders must be delivered Friday
                if self.delivery_date.weekday() != 4:
                    raise ValidationError(
                        'Thursday orders can only be delivered on Friday.'
                    )
    
    @staticmethod
    def is_order_day(check_date=None):
        """Check if given date (or today) is a valid order day"""
        if check_date is None:
            check_date = timezone.now().date()
        return check_date.weekday() in settings.ORDER_DAYS
    
    @staticmethod
    def is_delivery_day(check_date=None):
        """Check if given date (or today) is a valid delivery day"""
        if check_date is None:
            check_date = timezone.now().date()
        return check_date.weekday() in settings.DELIVERY_DAYS
    
    def __str__(self):
        return f"Order {self.order_number} - {self.restaurant.email if self.restaurant else 'Unknown'}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit = models.CharField(max_length=20, null=True, blank=True)  # kg, bunch, piece, etc.
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # AI parsing tracking
    original_text = models.CharField(max_length=200, blank=True)  # "1 x onions"
    confidence_score = models.FloatField(null=True, blank=True)  # AI parsing confidence
    manually_corrected = models.BooleanField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate total price
        self.total_price = self.quantity * self.price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}{self.unit}" 