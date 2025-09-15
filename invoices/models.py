from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

class Invoice(models.Model):
    """
    Customer invoices for orders
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic info
    invoice_number = models.CharField(max_length=50, unique=True)
    order = models.OneToOneField('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice')
    customer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='invoices')
    
    # Dates
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Financial details
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('15.00'),  # South African VAT
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Status and notes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notes = models.TextField(blank=True)
    payment_terms = models.CharField(max_length=100, default='Net 30', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-invoice_date']
        
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number
            today = timezone.now().date()
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=f"INV{today.year}"
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.invoice_number = f"INV{today.year}-{new_num:05d}"
        
        if not self.due_date:
            # Default to 30 days from invoice date
            self.due_date = self.invoice_date + timedelta(days=30)
        
        # Calculate totals
        self.tax_amount = (self.subtotal - self.discount_amount) * (self.tax_rate / 100)
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        
        super().save(*args, **kwargs)
    
    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid
    
    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.status not in ['paid', 'cancelled']
    
    @property
    def days_overdue(self):
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0

class InvoiceItem(models.Model):
    """
    Individual line items on an invoice
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    order_item = models.OneToOneField('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_item')
    
    # Product details (snapshot at time of invoice)
    product_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Quantities and pricing
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    line_total = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product_name']
        
    def __str__(self):
        return f"{self.product_name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Payment(models.Model):
    """
    Payments received against invoices
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_date = models.DateField(null=True, blank=True)
    
    # Reference details
    reference_number = models.CharField(max_length=100, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Processing
    processed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
        
    def __str__(self):
        return f"Payment R{self.amount} for {self.invoice.invoice_number}"

class CreditNote(models.Model):
    """
    Credit notes for returns, discounts, or corrections
    """
    REASON_CHOICES = [
        ('return', 'Product Return'),
        ('damage', 'Damaged Goods'),
        ('discount', 'Discount Applied'),
        ('correction', 'Invoice Correction'),
        ('goodwill', 'Goodwill Gesture'),
        ('other', 'Other'),
    ]
    
    # Basic info
    credit_note_number = models.CharField(max_length=50, unique=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='credit_notes')
    
    # Details
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField()
    
    # Dates
    credit_date = models.DateField(null=True, blank=True)
    
    # Processing
    approved_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-credit_date']
        
    def __str__(self):
        return f"Credit Note {self.credit_note_number} - R{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.credit_note_number:
            # Generate credit note number
            today = timezone.now().date()
            last_cn = CreditNote.objects.filter(
                credit_note_number__startswith=f"CN{today.year}"
            ).order_by('-credit_note_number').first()
            
            if last_cn:
                last_num = int(last_cn.credit_note_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.credit_note_number = f"CN{today.year}-{new_num:05d}"
        
        super().save(*args, **kwargs)