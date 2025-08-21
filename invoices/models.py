from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

User = get_user_model()

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    restaurant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            date_str = timezone.now().strftime('%Y%m')
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=f'INV-{date_str}'
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.invoice_number = f'INV-{date_str}-{new_number:04d}'
        
        if not self.due_date:
            self.due_date = self.issue_date + timedelta(days=30)
        
        self.tax_amount = self.subtotal * Decimal('0.15')
        self.total_amount = self.subtotal + self.tax_amount
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.restaurant.email}" 