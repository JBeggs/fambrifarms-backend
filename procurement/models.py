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
        supplier_name = self.supplier.name if self.supplier else 'No Supplier'
        return f"{self.po_number} ({supplier_name})"
    
    @classmethod
    def create_from_order(cls, order, supplier=None, inherit_dates=True):
        """
        Create a purchase order from an existing order with optional date inheritance
        
        Args:
            order: Order instance to create PO from
            supplier: Supplier instance (optional)
            inherit_dates: Whether to inherit dates from the order for backdating
        """
        po = cls(
            order=order,
            supplier=supplier,
            notes=f"Generated from order {order.order_number}"
        )
        
        if inherit_dates:
            po._inherit_order_dates = True
            po.order_date = order.order_date
            po.expected_delivery_date = order.delivery_date
        
        po.save()
        return po
    
    def save(self, *args, **kwargs):
        if not self.po_number:
            # Generate PO number - use order date if available for historical accuracy
            po_year = self.order.order_date.year if self.order else timezone.now().year
            
            last_po = PurchaseOrder.objects.filter(
                po_number__startswith=f"PO{po_year}"
            ).order_by('-po_number').first()
            
            if last_po:
                last_num = int(last_po.po_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.po_number = f"PO{po_year}-{new_num:04d}"
        
        # Inherit dates from related order for historical accuracy
        if self.order and hasattr(self, '_inherit_order_dates'):
            # Use order date as PO date for backdating
            if not hasattr(self, '_order_date_set'):
                self.order_date = self.order.order_date
                self._order_date_set = True
            
            # Set expected delivery date based on order delivery date
            if not self.expected_delivery_date:
                self.expected_delivery_date = self.order.delivery_date
        
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
    quantity_received = models.PositiveIntegerField(null=True, blank=True)
    
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
    received_date = models.DateTimeField(null=True, blank=True)
    
    # Quality check
    quality_check_passed = models.BooleanField(null=True, blank=True)
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
    )
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['po_item__product__name']
        
    def __str__(self):
        return f"{self.po_item.product.name} x{self.quantity_received}"