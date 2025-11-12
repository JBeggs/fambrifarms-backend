from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

def get_unit_choices():
    """Get unit choices dynamically from database"""
    from settings.models import UnitOfMeasure
    try:
        return [(unit.name, unit.display_name) for unit in UnitOfMeasure.objects.filter(is_active=True).order_by('sort_order')]
    except:
        # Fallback to hardcoded choices if database is not available
        return [
            ('kg', 'Kilogram'), ('g', 'Gram'), ('piece', 'Piece'), ('each', 'Each'),
            ('head', 'Head'), ('bunch', 'Bunch'), ('box', 'Box'), ('bag', 'Bag'),
            ('punnet', 'Punnet'), ('packet', 'Packet'), ('crate', 'Crate'),
            ('tray', 'Tray'), ('bundle', 'Bundle'), ('L', 'Liter'), ('ml', 'Milliliter'),
        ]

class Product(models.Model):
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    unit = models.CharField(max_length=20, choices=get_unit_choices, default='piece')
    stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('5.00'))
    is_active = models.BooleanField(default=True)
    needs_setup = models.BooleanField(default=False, help_text="Product was auto-created and needs pricing/inventory setup")
    unlimited_stock = models.BooleanField(
        default=False,
        help_text="Product is always available (e.g., garden-grown). Orders will not reserve stock."
    )
    
    # Procurement management
    procurement_supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='procured_products',
        help_text='Primary supplier for market procurement. NULL = use Fambri garden/no procurement needed.'
    )
    
    # Supplier cost tracking
    supplier_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Current cost from supplier'
    )
    
    cost_unit = models.CharField(
        max_length=20,
        choices=[
            ('per_kg', 'Per kilogram'),
            ('per_unit', 'Per unit/each'),
            ('per_package', 'Per package'),
        ],
        default='per_kg'
    )
    
    last_supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_supplied'
    )
    
    last_cost_update = models.DateField(
        null=True,
        blank=True,
        help_text='Date of last supplier cost update'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_customer_price(self, customer):
        """Get customer-specific price from active price list, fallback to base price"""
        from datetime import date
        from inventory.models import CustomerPriceListItem
        
        # Try to find customer-specific price from active price list
        try:
            today = date.today()
            price_item = CustomerPriceListItem.objects.filter(
                price_list__customer=customer,
                price_list__effective_from__lte=today,
                price_list__effective_until__gte=today,
                price_list__status='active',
                product=self
            ).select_related('price_list').first()
            
            if price_item:
                return price_item.customer_price_incl_vat
        except Exception as e:
            # If any error occurs, fall back to base price
            print(f"[PRODUCT_PRICING] Error getting customer price: {e}")
            pass
        
        # Fallback to base product price
        return self.price
    
    def __str__(self):
        return f"{self.name} - R{self.price}/{self.unit}"
    
    class Meta:
        ordering = ['department__name', 'name']
        unique_together = ['name', 'department', 'unit']

class ProductAlert(models.Model):
    ALERT_TYPES = [
        ('needs_setup', 'Needs Setup'),
        ('low_stock', 'Low Stock'),
        ('no_price', 'No Price Set'),
        ('missing_recipe', 'Missing Recipe'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_by_order = models.CharField(max_length=50, blank=True, help_text="Order number that triggered this alert")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.get_alert_type_display()}"
    
    class Meta:
        ordering = ['-created_at']

class ProcurementBuffer(models.Model):
    """Intelligent buffer calculations for market purchases"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='procurement_buffer')
    
    # Wastage factors
    spoilage_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.15,
        help_text="Expected spoilage rate (0.15 = 15%)"
    )
    cutting_waste_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.10,
        help_text="Waste from cutting/trimming (0.10 = 10%)"
    )
    quality_rejection_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.05,
        help_text="Rate of quality rejections (0.05 = 5%)"
    )
    
    # Buffer calculation
    total_buffer_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=0.30,
        help_text="Total buffer rate (auto-calculated)"
    )
    
    # Market-specific settings
    market_pack_size = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        help_text="Standard market pack size (e.g., 10kg boxes)"
    )
    market_pack_unit = models.CharField(
        max_length=20, choices=get_unit_choices, default='kg'
    )
    
    # Seasonality
    is_seasonal = models.BooleanField(default=False)
    peak_season_months = models.JSONField(
        default=list, 
        help_text="List of peak season months [1-12]"
    )
    peak_season_buffer_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.5,
        help_text="Extra buffer during peak season"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Auto-calculate total buffer rate
        self.total_buffer_rate = (
            self.spoilage_rate + 
            self.cutting_waste_rate + 
            self.quality_rejection_rate
        )
        super().save(*args, **kwargs)
    
    def calculate_market_quantity(self, needed_quantity):
        """Calculate how much to buy at market based on needed quantity"""
        from datetime import datetime
        from decimal import Decimal
        from .models_business_settings import BusinessSettings
        
        # Convert to Decimal for consistent math
        needed_quantity = Decimal(str(needed_quantity))
        
        # Check if buffer calculations are globally disabled
        business_settings = BusinessSettings.get_settings()
        if not business_settings.enable_buffer_calculations:
            print(f"🚫 Buffer calculations DISABLED globally for {self.product.name}")
            # Return needed quantity without any buffers
            return {
                'needed_quantity': float(needed_quantity),
                'buffer_applied': float(needed_quantity),
                'market_quantity': float(needed_quantity),
                'buffer_rate': 0.0,
                'seasonal_multiplier': 1.0,
                'market_packs': 1
            }
        
        # Apply buffer
        buffered_quantity = needed_quantity * (1 + self.total_buffer_rate)
        
        # Apply seasonal multiplier if in peak season
        current_month = datetime.now().month
        if self.is_seasonal and current_month in self.peak_season_months:
            buffered_quantity *= self.peak_season_buffer_multiplier
        
        # Round up to nearest market pack size
        if self.market_pack_size > 1:
            packs_needed = int((buffered_quantity / self.market_pack_size).__ceil__())
            market_quantity = packs_needed * self.market_pack_size
        else:
            market_quantity = buffered_quantity
        
        result = {
            'needed_quantity': float(needed_quantity),
            'buffer_applied': float(buffered_quantity),
            'market_quantity': float(market_quantity),
            'buffer_rate': float(self.total_buffer_rate),
            'seasonal_multiplier': float(self.peak_season_buffer_multiplier) if current_month in self.peak_season_months else 1.0,
            'market_packs': int(market_quantity / self.market_pack_size) if self.market_pack_size > 1 else 1
        }
        
        print(f"📊 Buffer calc for {self.product.name}: {float(needed_quantity):.1f} → {float(market_quantity):.1f} (rate: {float(self.total_buffer_rate):.1%}, pack: {float(self.market_pack_size)})")
        
        return result
    
    def __str__(self):
        return f"Buffer for {self.product.name} ({self.total_buffer_rate:.1%})"
    
    class Meta:
        ordering = ['product__name']

class MarketProcurementRecommendation(models.Model):
    """AI-generated recommendations for market purchases"""
    
    # Recommendation metadata
    created_at = models.DateTimeField(auto_now_add=True)
    for_date = models.DateField(help_text="Market trip date")
    total_estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved by Karl'),
        ('purchased', 'Purchased at Market'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Analysis data
    analysis_data = models.JSONField(
        default=dict,
        help_text="Detailed analysis: orders, stock levels, predictions"
    )
    
    # Notes
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Market Recommendation for {self.for_date} (R{self.total_estimated_cost})"
    
    class Meta:
        ordering = ['-created_at']

class MarketProcurementItem(models.Model):
    """Individual items in a market procurement recommendation"""
    recommendation = models.ForeignKey(
        MarketProcurementRecommendation, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    # INTEGRATION: Link to supplier products for unified procurement
    preferred_supplier = models.ForeignKey(
        'suppliers.Supplier', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text="Recommended supplier based on Fambri-first logic"
    )
    supplier_product = models.ForeignKey(
        'suppliers.SupplierProduct',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Specific supplier product with pricing and availability"
    )
    
    # Quantities
    needed_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    recommended_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Pricing (now supplier-aware)
    estimated_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    estimated_total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    supplier_unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True,
        help_text="Actual supplier price if available"
    )
    
    # Supplier metrics integration
    supplier_quality_rating = models.DecimalField(
        max_digits=3, decimal_places=2,
        null=True, blank=True,
        help_text="Quality rating from supplier performance tracking"
    )
    supplier_lead_time_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Lead time from supplier"
    )
    is_fambri_available = models.BooleanField(
        default=False,
        help_text="Whether Fambri Internal can supply this item"
    )
    
    # Reasoning
    reasoning = models.TextField(help_text="Why this quantity is recommended")
    priority = models.CharField(
        max_length=20,
        choices=[
            ('critical', 'Critical - Out of Stock'),
            ('high', 'High - Low Stock'),
            ('medium', 'Medium - Upcoming Orders'),
            ('low', 'Low - Buffer Stock'),
        ],
        default='medium'
    )
    
    # Source orders/predictions
    source_orders = models.JSONField(
        default=list,
        help_text="Order IDs that drove this recommendation"
    )
    
    # Procurement method tracking
    procurement_method = models.CharField(
        max_length=20,
        choices=[
            ('market', 'Market Purchase'),
            ('supplier', 'Direct Supplier'),
            ('fambri', 'Fambri Internal'),
            ('mixed', 'Multi-Supplier Split'),
        ],
        default='market',
        help_text="Recommended procurement method"
    )
    
    def __str__(self):
        return f"{self.product.name} x{self.recommended_quantity} ({self.priority})"
    
    class Meta:
        ordering = ['priority', 'product__name']

class Recipe(models.Model):
    """Recipe/ingredient breakdown for complex products"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='product_recipe')
    ingredients = models.JSONField(default=list, help_text="List of ingredient items with quantities")
    instructions = models.TextField(blank=True)
    prep_time_minutes = models.PositiveIntegerField(default=30)
    yield_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    yield_unit = models.CharField(max_length=20, choices=get_unit_choices, default='piece')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Recipe for {self.product.name}"
    
    class Meta:
        ordering = ['product__name']