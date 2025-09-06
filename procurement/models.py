from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

class PurchaseOrder(models.Model):
    """
    Purchase Orders sent to suppliers
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed by Supplier'),
        ('partial', 'Partially Received'),
        ('received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic info
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE, related_name='purchase_orders', null=True, blank=True)
    sales_rep = models.ForeignKey('suppliers.SalesRep', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, related_name='purchase_orders', null=True, blank=True)
    
    # Status and dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(default=timezone.now)
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    
    # Financial
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Notes and tracking
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"PO-{self.po_number} ({self.supplier.name})"
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            # Generate PO number
            last_po = PurchaseOrder.objects.filter(
                po_number__startswith=f"PO{timezone.now().year}"
            ).order_by('-po_number').first()
            
            if last_po:
                last_num = int(last_po.po_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.po_number = f"PO{timezone.now().year}-{new_num:04d}"
        
        super().save(*args, **kwargs)

class PurchaseOrderItem(models.Model):
    """
    Individual items in a Purchase Order
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Quantities
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['product__name']
        
    def __str__(self):
        return f"{self.product.name} x{self.quantity_ordered}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity_ordered * self.unit_price
        super().save(*args, **kwargs)
    
    @property
    def quantity_pending(self):
        return self.quantity_ordered - self.quantity_received
    
    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered

class PurchaseOrderReceipt(models.Model):
    """
    Record of goods received against Purchase Orders
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='receipts')
    received_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    received_date = models.DateTimeField(default=timezone.now)
    
    # Quality check
    quality_check_passed = models.BooleanField(default=True)
    quality_notes = models.TextField(blank=True)
    
    # Documentation
    delivery_note_number = models.CharField(max_length=100, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-received_date']
        
    def __str__(self):
        return f"Receipt for {self.purchase_order.po_number} on {self.received_date.date()}"

class PurchaseOrderReceiptItem(models.Model):
    """
    Individual items received in a receipt
    """
    receipt = models.ForeignKey(PurchaseOrderReceipt, on_delete=models.CASCADE, related_name='items')
    po_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.CASCADE)
    quantity_received = models.PositiveIntegerField()
    
    # Quality and condition
    condition_rating = models.CharField(
        max_length=20,
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        default='good'
    )
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['po_item__product__name']
        
    def __str__(self):
        return f"{self.po_item.product.name} x{self.quantity_received}"