from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Supplier(models.Model):
    """
    Supplier/vendor that provides products to Fambri Farms
    """
    SUPPLIER_TYPE_CHOICES = [
        ('internal', 'Internal Farm'),
        ('external', 'External Supplier'),
    ]
    
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    description = models.TextField(blank=True, help_text="Description of supplier and specialties")
    
    supplier_type = models.CharField(
        max_length=20, 
        choices=SUPPLIER_TYPE_CHOICES, 
        default='external',
        help_text="Type of supplier - internal farm or external supplier"
    )
    
    registration_number = models.CharField(max_length=50, blank=True)
    tax_number = models.CharField(max_length=50, blank=True)
    
    is_active = models.BooleanField(default=True)
    payment_terms_days = models.PositiveIntegerField(default=30, help_text="Payment terms in days")
    lead_time_days = models.PositiveIntegerField(default=3, help_text="Lead time in days")
    minimum_order_value = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    @property
    def total_orders(self):
        """Calculate total number of orders containing products from this supplier"""
        # Import here to avoid circular imports
        from orders.models import OrderItem
        # Count distinct orders that have items from products supplied by this supplier
        return OrderItem.objects.filter(
            product__supplier_products__supplier=self
        ).values('order').distinct().count()
    
    @property
    def total_order_value(self):
        """Calculate total value of all order items from this supplier"""
        from orders.models import OrderItem
        from django.db.models import Sum
        result = OrderItem.objects.filter(
            product__supplier_products__supplier=self
        ).aggregate(total=Sum('total_price'))
        return float(result['total'] or 0.0)
    
    @property
    def last_order_date(self):
        """Get the date of the most recent order containing products from this supplier"""
        from orders.models import OrderItem
        last_item = OrderItem.objects.filter(
            product__supplier_products__supplier=self
        ).select_related('order').order_by('-order__created_at').first()
        return last_item.order.created_at.date() if last_item else None

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
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False, help_text='Primary contact for this supplier')
    
    # Performance tracking
    total_orders = models.PositiveIntegerField(default=0)
    last_contact_date = models.DateField(null=True, blank=True)
    
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
    supplier_product_code = models.CharField(max_length=100, blank=True, help_text='Supplier internal product code')
    supplier_product_name = models.CharField(max_length=200, blank=True, help_text='Product name as per supplier')
    supplier_category_code = models.CharField(max_length=10, blank=True, help_text='Supplier category code (BT, FRE, NVL, PRO, etc.)')
    
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


class SupplierPriceList(models.Model):
    """
    Price lists received from suppliers
    """
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='price_lists')
    list_date = models.DateField(help_text='Date on the price list document')
    received_date = models.DateTimeField(auto_now_add=True)
    file_reference = models.CharField(max_length=200, blank=True, help_text='Reference to source file/image')
    is_processed = models.BooleanField(default=False, help_text='Has this price list been processed and matched?')
    notes = models.TextField(blank=True)
    
    # Processing stats
    total_items = models.PositiveIntegerField(null=True, blank=True)
    matched_items = models.PositiveIntegerField(null=True, blank=True)
    unmatched_items = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-list_date', '-received_date']
        unique_together = ['supplier', 'list_date']
        
    def __str__(self):
        return f"{self.supplier.name} - Price List {self.list_date}"
    
    @property
    def match_percentage(self):
        """Calculate percentage of items matched to products"""
        if not self.total_items:
            return 0
        return round((self.matched_items or 0) / self.total_items * 100, 1)


class SupplierPriceListItem(models.Model):
    """
    Individual items from supplier price lists
    """
    price_list = models.ForeignKey(SupplierPriceList, on_delete=models.CASCADE, related_name='items')
    
    # Raw data from supplier list
    supplier_code = models.CharField(max_length=50, help_text='Full supplier product code')
    product_description = models.CharField(max_length=200, help_text='Product description from supplier')
    category_code = models.CharField(max_length=10, help_text='Category code (BT, FRE, NVL, etc.)')
    
    # Quantities and pricing
    quantity = models.PositiveIntegerField(help_text='Quantity available')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])
    total_excl_vat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])
    total_incl_vat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])
    
    # Matching
    matched_product = models.ForeignKey('products.Product', null=True, blank=True, on_delete=models.SET_NULL, related_name='price_list_items')
    match_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Matching confidence score (0-100)')
    match_method = models.CharField(max_length=50, blank=True, help_text='How this item was matched (exact, fuzzy, manual, etc.)')
    is_manually_matched = models.BooleanField(default=False)
    
    # Status
    is_new_product = models.BooleanField(default=False, help_text='Flagged as potentially new product to add')
    needs_review = models.BooleanField(default=False, help_text='Requires manual review')
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category_code', 'product_description']
        unique_together = ['price_list', 'supplier_code']
        
    def __str__(self):
        return f"{self.product_description} - R{self.unit_price}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate totals if not provided
        if self.quantity and self.unit_price:
            if not self.total_excl_vat:
                self.total_excl_vat = self.quantity * self.unit_price
            if not self.total_incl_vat and self.vat_amount:
                self.total_incl_vat = self.total_excl_vat + self.vat_amount
            elif not self.total_incl_vat:
                self.total_incl_vat = self.total_excl_vat
                
        super().save(*args, **kwargs)