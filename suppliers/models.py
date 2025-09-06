from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Supplier(models.Model):
    """
    Supplier/vendor that provides products to Fambri Farms
    """
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Business details
    registration_number = models.CharField(max_length=50, blank=True)
    tax_number = models.CharField(max_length=50, blank=True)
    
    # Status and settings
    is_active = models.BooleanField(null=True, blank=True)
    payment_terms_days = models.PositiveIntegerField(null=True, blank=True)
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    minimum_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class SalesRep(models.Model):
    """
    Sales representatives for suppliers
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='sales_reps')
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    position = models.CharField(max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(null=True, blank=True)
    is_primary = models.BooleanField(null=True, blank=True, help_text='Primary contact for this supplier')
    
    # Performance tracking
    total_orders = models.PositiveIntegerField(null=True, blank=True)
    last_contact_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', 'name']
        unique_together = ['supplier', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.supplier.name})"

class SupplierProduct(models.Model):
    """
    Products available from suppliers with pricing and availability
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='supplier_products')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='supplier_products')
    
    # Supplier-specific details
    supplier_product_code = models.CharField(max_length=100, blank=True)
    supplier_product_name = models.CharField(max_length=200, blank=True)
    
    # Pricing
    supplier_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, null=True, blank=True)
    
    # Availability
    is_available = models.BooleanField(null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(null=True, blank=True)
    minimum_order_quantity = models.PositiveIntegerField(null=True, blank=True)
    
    # Lead time (can override supplier default)
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)
    
    # Quality and performance tracking
    quality_rating = models.DecimalField(
        max_digits=3, decimal_places=2, 
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    last_order_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['supplier', 'product']
        ordering = ['supplier__name', 'product__name']
        
    def __str__(self):
        return f"{self.supplier.name} - {self.product.name}"
    
    def get_effective_lead_time(self):
        """Get lead time (product-specific or supplier default)"""
        return self.lead_time_days or self.supplier.lead_time_days