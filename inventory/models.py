from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import uuid

User = get_user_model()


class UnitOfMeasure(models.Model):
    """Standard units of measurement for inventory tracking"""
    name = models.CharField(max_length=50, unique=True)  # kg, grams, pieces, bunches
    abbreviation = models.CharField(max_length=10, unique=True)  # kg, g, pcs, bunch
    is_weight = models.BooleanField(default=True, help_text="True for weight-based, False for count-based")
    base_unit_multiplier = models.DecimalField(max_digits=10, decimal_places=4, default=1.0, help_text="For conversion to base unit")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class RawMaterial(models.Model):
    """Raw materials/ingredients that are purchased from suppliers"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit code")
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE)
    
    # Quality and Safety
    requires_batch_tracking = models.BooleanField(null=True, blank=True)
    shelf_life_days = models.IntegerField(null=True, blank=True, help_text="Shelf life in days")
    storage_temperature_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    storage_temperature_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Inventory Levels
    minimum_stock_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    maximum_stock_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def current_stock_level(self):
        """Calculate current stock level from all batches"""
        return sum([batch.available_quantity for batch in self.batches.filter(is_active=True)])
    
    @property
    def needs_reorder(self):
        """Check if stock level is below reorder point"""
        return self.current_stock_level <= self.reorder_level


class RawMaterialBatch(models.Model):
    """Individual batches of raw materials for traceability"""
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100, unique=True)
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.PROTECT,
        help_text="Supplier who provided this batch"
    )
    
    # Quantities
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    available_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    
    # Pricing
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    
    # Dates
    received_date = models.DateTimeField(null=True, blank=True)
    production_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Quality Control
    quality_grade = models.CharField(max_length=10, choices=[
        ('A', 'Grade A - Premium'),
        ('B', 'Grade B - Standard'),
        ('C', 'Grade C - Basic'),
        ('R', 'Rejected')
    ])
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        if not self.batch_number:
            # Generate batch number: RM-YYYYMMDD-XXXX
            date_str = timezone.now().strftime('%Y%m%d')
            last_batch = RawMaterialBatch.objects.filter(
                batch_number__startswith=f'RM-{date_str}'
            ).order_by('-batch_number').first()
            
            if last_batch:
                last_num = int(last_batch.batch_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.batch_number = f'RM-{date_str}-{new_num:04d}'
        
        if self.available_quantity is None:
            self.available_quantity = self.received_quantity
            
        self.total_cost = self.received_quantity * self.unit_cost
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if batch is expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()
    
    @property
    def days_until_expiry(self):
        """Days until expiry (negative if already expired)"""
        if not self.expiry_date:
            return None
        from datetime import date
        return (self.expiry_date - date.today()).days
    
    def __str__(self):
        return f"{self.raw_material.name} - {self.batch_number}"


class ProductionRecipe(models.Model):
    """Defines how raw materials are converted into finished products"""
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='recipes')
    version = models.CharField(max_length=10)
    
    # Recipe Details
    output_quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    output_unit = models.ForeignKey(UnitOfMeasure, on_delete=models.CASCADE, related_name='recipe_outputs')
    
    # Processing
    processing_time_minutes = models.IntegerField(null=True, blank=True)
    processing_notes = models.TextField(blank=True)
    yield_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                         validators=[MinValueValidator(1), MaxValueValidator(100)])
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['product', 'version']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - Recipe v{self.version}"
    
    @property
    def total_raw_material_cost(self):
        """Calculate total cost of raw materials for this recipe"""
        return sum([ingredient.total_cost for ingredient in self.ingredients.all()])
    
    @property
    def cost_per_unit(self):
        """Cost per unit of output"""
        if self.output_quantity > 0:
            return self.total_raw_material_cost / self.output_quantity
        return Decimal('0.00')


class RecipeIngredient(models.Model):
    """Individual raw materials used in a recipe"""
    recipe = models.ForeignKey(ProductionRecipe, on_delete=models.CASCADE, related_name='ingredients')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    notes = models.CharField(max_length=200, blank=True)
    
    class Meta:
        unique_together = ['recipe', 'raw_material']
    
    def __str__(self):
        return f"{self.recipe.product.name}: {self.quantity} {self.raw_material.unit.abbreviation} {self.raw_material.name}"
    
    @property
    def estimated_cost(self):
        """Estimate cost based on average raw material cost"""
        # This would calculate based on FIFO or weighted average
        # For now, using latest batch cost
        latest_batch = self.raw_material.batches.filter(is_active=True).order_by('-received_date').first()
        if latest_batch:
            return self.quantity * latest_batch.unit_cost
        return Decimal('0.00')
    
    @property
    def total_cost(self):
        return self.estimated_cost


class FinishedInventory(models.Model):
    """Tracks finished product inventory ready for sale"""
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='inventory')
    
    # Stock Levels
    available_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reserved_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # For confirmed orders
    minimum_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Costing
    average_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.product.name} - Available: {self.available_quantity}"
    
    @property
    def total_quantity(self):
        """Total quantity (available + reserved)"""
        available = self.available_quantity or Decimal('0.00')
        reserved = self.reserved_quantity or Decimal('0.00')
        return available + reserved
    
    @property
    def needs_production(self):
        """Check if production is needed"""
        available = self.available_quantity or Decimal('0.00')
        reorder = self.reorder_level or Decimal('0.00')
        return available <= reorder
    
    def reserve_stock(self, quantity):
        """Reserve stock for an order"""
        available = self.available_quantity or Decimal('0.00')
        reserved = self.reserved_quantity or Decimal('0.00')
        
        if available >= quantity:
            self.available_quantity = available - quantity
            self.reserved_quantity = reserved + quantity
            self.save()
            return True
        return False
    
    def release_stock(self, quantity):
        """Release reserved stock (order cancelled)"""
        available = self.available_quantity or Decimal('0.00')
        reserved = self.reserved_quantity or Decimal('0.00')
        
        if reserved >= quantity:
            self.reserved_quantity = reserved - quantity
            self.available_quantity = available + quantity
            self.save()
            return True
        return False
    
    def sell_stock(self, quantity):
        """Sell reserved stock (order delivered)"""
        reserved = self.reserved_quantity or Decimal('0.00')
        
        if reserved >= quantity:
            self.reserved_quantity = reserved - quantity
            self.save()
            return True
        return False


class StockMovement(models.Model):
    """Audit trail for all stock movements"""
    MOVEMENT_TYPES = [
        # Raw Materials
        ('raw_receive', 'Raw Material Received'),
        ('raw_adjust', 'Raw Material Adjustment'),
        ('raw_consume', 'Raw Material Consumed in Production'),
        ('raw_waste', 'Raw Material Waste/Spoilage'),
        
        # Production
        ('production', 'Production Output'),
        ('production_waste', 'Production Waste'),
        
        # Finished Inventory
        ('finished_adjust', 'Finished Inventory Adjustment (Add)'),
        ('finished_set', 'Finished Inventory Set (Replace)'),
        ('finished_reserve', 'Stock Reserved for Order'),
        ('finished_release', 'Stock Released (Order Cancelled)'),
        ('finished_sell', 'Stock Sold (Order Delivered)'),
        ('finished_waste', 'Finished Product Waste'),
    ]
    
    # Movement Details
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    reference_number = models.CharField(max_length=50)  # Order number, batch number, etc.
    
    # What moved
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, null=True, blank=True)
    raw_material_batch = models.ForeignKey(RawMaterialBatch, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, null=True, blank=True)
    
    # Quantities
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Context
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.quantity} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class ProductionBatch(models.Model):
    """Records of production runs converting raw materials to finished products"""
    batch_number = models.CharField(max_length=100, unique=True)
    recipe = models.ForeignKey(ProductionRecipe, on_delete=models.CASCADE)
    
    # Production Details
    planned_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    actual_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    waste_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Timing
    planned_date = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # People
    planned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='planned_batches')
    produced_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='produced_batches')
    
    # Costing
    total_raw_material_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    overhead_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        if not self.batch_number:
            # Generate batch number: PB-YYYYMMDD-XXXX
            date_str = timezone.now().strftime('%Y%m%d')
            last_batch = ProductionBatch.objects.filter(
                batch_number__startswith=f'PB-{date_str}'
            ).order_by('-batch_number').first()
            
            if last_batch:
                last_num = int(last_batch.batch_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.batch_number = f'PB-{date_str}-{new_num:04d}'
        
        super().save(*args, **kwargs)
    
    @property
    def yield_percentage(self):
        """Calculate actual yield vs planned"""
        if self.planned_quantity and self.actual_quantity:
            return (self.actual_quantity / self.planned_quantity) * 100
        return 0
    
    @property
    def total_cost(self):
        """Total production cost"""
        return self.total_raw_material_cost + self.labor_cost + self.overhead_cost
    
    @property
    def cost_per_unit(self):
        """Cost per unit produced"""
        if self.actual_quantity and self.actual_quantity > 0:
            return self.total_cost / self.actual_quantity
        return Decimal('0.00')
    
    def __str__(self):
        return f"{self.batch_number} - {self.recipe.product.name}"


class StockAlert(models.Model):
    """Automated alerts for stock management"""
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('overstock', 'Overstock'),
        ('production_needed', 'Production Needed'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    
    # What triggered the alert
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, null=True, blank=True)
    raw_material_batch = models.ForeignKey(RawMaterialBatch, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, null=True, blank=True)
    
    # Alert Details
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ])
    
    # Status
    is_active = models.BooleanField(default=True)
    is_acknowledged = models.BooleanField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def acknowledge(self, user):
        """Mark alert as acknowledged"""
        self.is_acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.message[:50]}..."


class StockAnalysis(models.Model):
    """Analyze customer orders against available stock"""
    analysis_date = models.DateTimeField(auto_now_add=True)
    order_period_start = models.DateField(help_text="Monday order date")
    order_period_end = models.DateField(help_text="Thursday order date")
    
    # Analysis Results
    total_orders_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total value of all orders in this period"
    )
    total_stock_value = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total value of available stock"
    )
    fulfillment_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Percentage of orders that can be fulfilled"
    )
    
    # Status
    STATUS_CHOICES = [
        ('analyzing', 'Analyzing'),
        ('completed', 'Completed'),
        ('action_required', 'Action Required'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-analysis_date']
        verbose_name = "Stock Analysis"
        verbose_name_plural = "Stock Analyses"
    
    def __str__(self):
        return f"Stock Analysis {self.analysis_date.strftime('%Y-%m-%d')} - {self.get_status_display()}"
    
    @property
    def shortfall_value(self):
        """Calculate total value of stock shortfalls"""
        return sum([item.shortfall_value for item in self.items.all()])
    
    @property
    def items_needing_procurement(self):
        """Get items that need procurement"""
        return self.items.filter(needs_procurement=True)


class StockAnalysisItem(models.Model):
    """Individual product analysis within a stock analysis"""
    analysis = models.ForeignKey(StockAnalysis, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    
    # Demand vs Supply
    total_ordered_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total quantity ordered by customers"
    )
    available_stock_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Available stock quantity"
    )
    shortfall_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Quantity shortfall (ordered - available)"
    )
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Current unit price"
    )
    
    # Recommendations
    needs_procurement = models.BooleanField(
        help_text="Whether this item needs to be procured"
    )
    suggested_order_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Suggested quantity to order from supplier"
    )
    suggested_supplier = models.ForeignKey(
        'suppliers.Supplier', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Recommended supplier for this item"
    )
    
    # Urgency
    URGENCY_CHOICES = [
        ('low', 'Low - Normal Reorder'),
        ('medium', 'Medium - Stock Running Low'),
        ('high', 'High - Critical Shortage'),
        ('urgent', 'Urgent - Out of Stock'),
    ]
    urgency_level = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    
    class Meta:
        unique_together = ['analysis', 'product']
        ordering = ['-urgency_level', '-shortfall_quantity']
    
    def save(self, *args, **kwargs):
        # Calculate shortfall
        if self.total_ordered_quantity and self.available_stock_quantity:
            self.shortfall_quantity = max(
                Decimal('0.00'),
                self.total_ordered_quantity - self.available_stock_quantity
            )
        
        # Determine if procurement is needed
        self.needs_procurement = self.shortfall_quantity > 0
        
        # Set urgency level based on shortfall
        if self.shortfall_quantity <= 0:
            self.urgency_level = 'low'
        elif self.available_stock_quantity <= 0:
            self.urgency_level = 'urgent'
        elif self.shortfall_quantity >= (self.total_ordered_quantity * Decimal('0.5')):
            self.urgency_level = 'high'
        else:
            self.urgency_level = 'medium'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.name} - Shortfall: {self.shortfall_quantity}"
    
    @property
    def shortfall_value(self):
        """Calculate monetary value of shortfall"""
        return self.shortfall_quantity * self.unit_price
    
    @property
    def fulfillment_percentage(self):
        """Calculate what percentage of demand can be fulfilled"""
        if self.total_ordered_quantity > 0:
            fulfilled = min(self.total_ordered_quantity, self.available_stock_quantity)
            return (fulfilled / self.total_ordered_quantity) * 100
        return Decimal('100.00')


# Market Price Tracking and Procurement Intelligence Models

class MarketPrice(models.Model):
    """Track market prices from supplier invoices for procurement intelligence"""
    
    # Supplier and invoice information
    supplier_name = models.CharField(
        max_length=100, 
        help_text="Name of the market/supplier (e.g., 'Tshwane Market')"
    )
    invoice_date = models.DateField(
        help_text="Date of the market invoice"
    )
    invoice_reference = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Invoice number or reference"
    )
    
    # Product and pricing information
    product_name = models.CharField(
        max_length=200, 
        help_text="Product name as it appears on invoice"
    )
    matched_product = models.ForeignKey(
        'products.Product', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Matched product in our system"
    )
    
    # Pricing details
    unit_price_excl_vat = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Unit price excluding VAT"
    )
    vat_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="VAT amount per unit"
    )
    unit_price_incl_vat = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Unit price including VAT"
    )
    quantity_unit = models.CharField(
        max_length=50, 
        default="each",
        help_text="Unit of measurement (each, kg, box, etc.)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this price record is active"
    )
    
    class Meta:
        db_table = 'inventory_market_price'
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['supplier_name', 'invoice_date']),
            models.Index(fields=['product_name']),
            models.Index(fields=['matched_product', 'invoice_date']),
        ]
        unique_together = ['supplier_name', 'invoice_date', 'product_name']
    
    def __str__(self):
        return f"{self.product_name} - R{self.unit_price_incl_vat} ({self.supplier_name}, {self.invoice_date})"
    
    @property
    def vat_percentage(self):
        """Calculate VAT percentage"""
        if self.unit_price_excl_vat > 0:
            return (self.vat_amount / self.unit_price_excl_vat) * 100
        return Decimal('0.00')
    
    def save(self, *args, **kwargs):
        """Auto-calculate VAT inclusive price if not provided"""
        if not self.unit_price_incl_vat:
            self.unit_price_incl_vat = self.unit_price_excl_vat + self.vat_amount
        super().save(*args, **kwargs)


class ProcurementRecommendation(models.Model):
    """AI-powered procurement recommendations based on stock analysis and market prices"""
    
    # Link to stock analysis
    stock_analysis = models.ForeignKey(
        StockAnalysis, 
        on_delete=models.CASCADE,
        related_name='procurement_recommendations'
    )
    product = models.ForeignKey(
        'products.Product', 
        on_delete=models.CASCADE
    )
    
    # Recommendation details
    recommended_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Recommended quantity to procure"
    )
    recommended_supplier = models.ForeignKey(
        'suppliers.Supplier', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Recommended supplier based on price and reliability"
    )
    
    # Market intelligence
    current_market_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text="Latest market price for this product"
    )
    average_market_price_30d = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text="30-day average market price"
    )
    price_trend = models.CharField(
        max_length=20,
        choices=[
            ('rising', 'Rising'),
            ('falling', 'Falling'), 
            ('stable', 'Stable'),
            ('volatile', 'Volatile')
        ],
        default='stable',
        help_text="Price trend analysis"
    )
    
    # Urgency and timing
    URGENCY_CHOICES = [
        ('low', 'Low - Normal Reorder'),
        ('medium', 'Medium - Stock Running Low'),
        ('high', 'High - Critical Shortage'),
        ('urgent', 'Urgent - Out of Stock')
    ]
    urgency_level = models.CharField(
        max_length=20, 
        choices=URGENCY_CHOICES,
        help_text="Procurement urgency level"
    )
    recommended_order_date = models.DateField(
        help_text="Recommended date to place order"
    )
    expected_delivery_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Expected delivery date"
    )
    
    # Financial analysis
    estimated_total_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Estimated total cost for recommended quantity"
    )
    potential_savings = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Potential savings vs. alternative suppliers"
    )
    
    # Status tracking
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('ordered', 'Order Placed'),
        ('received', 'Received'),
        ('rejected', 'Rejected')
    ]
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'inventory_procurement_recommendation'
        ordering = ['-urgency_level', '-created_at']
        indexes = [
            models.Index(fields=['status', 'urgency_level']),
            models.Index(fields=['recommended_order_date']),
            models.Index(fields=['product', 'status']),
        ]
    
    def __str__(self):
        return f"Procure {self.recommended_quantity} {self.product.name} ({self.urgency_level})"
    
    @property
    def days_until_recommended_order(self):
        """Calculate days until recommended order date"""
        from datetime import date
        return (self.recommended_order_date - date.today()).days
    
    @property
    def is_overdue(self):
        """Check if recommendation is overdue"""
        from datetime import date
        return self.recommended_order_date < date.today() and self.status == 'pending'
    
    def save(self, *args, **kwargs):
        """Auto-calculate estimated total cost"""
        if self.current_market_price:
            self.estimated_total_cost = self.recommended_quantity * self.current_market_price
        super().save(*args, **kwargs)


class PriceAlert(models.Model):
    """Price volatility alerts for procurement decision making"""
    
    product = models.ForeignKey(
        'products.Product', 
        on_delete=models.CASCADE
    )
    
    # Alert configuration
    alert_type = models.CharField(
        max_length=20,
        choices=[
            ('price_spike', 'Price Spike'),
            ('price_drop', 'Price Drop'),
            ('volatility', 'High Volatility'),
            ('trend_change', 'Trend Change')
        ],
        help_text="Type of price alert"
    )
    threshold_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Percentage threshold for alert trigger"
    )
    
    # Price data
    baseline_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Baseline price for comparison"
    )
    current_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Current market price that triggered alert"
    )
    price_change_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        help_text="Percentage change from baseline"
    )
    
    # Alert status
    alert_triggered_at = models.DateTimeField(auto_now_add=True)
    is_acknowledged = models.BooleanField(
        default=False,
        help_text="Whether alert has been acknowledged"
    )
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Recommendation
    recommended_action = models.TextField(
        blank=True,
        help_text="AI-generated recommendation based on price change"
    )
    
    class Meta:
        db_table = 'inventory_price_alert'
        ordering = ['-alert_triggered_at']
        indexes = [
            models.Index(fields=['product', 'alert_type']),
            models.Index(fields=['is_acknowledged', 'alert_triggered_at']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.alert_type} ({self.price_change_percentage:+.1f}%)"
    
    def acknowledge(self, user):
        """Acknowledge the alert"""
        from django.utils import timezone
        self.is_acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()


# Dynamic Price Management Models

class PricingRule(models.Model):
    """Define pricing rules and markup strategies for different customer segments"""
    
    name = models.CharField(
        max_length=100,
        help_text="Name of the pricing rule (e.g., 'Premium Restaurants', 'Budget Cafes')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of when and how this rule applies"
    )
    
    # Rule application criteria
    customer_segment = models.CharField(
        max_length=50,
        choices=[
            ('premium', 'Premium Restaurants'),
            ('standard', 'Standard Restaurants'),
            ('budget', 'Budget Cafes'),
            ('wholesale', 'Wholesale Buyers'),
            ('retail', 'Retail Customers')
        ],
        help_text="Customer segment this rule applies to"
    )
    
    # Markup configuration
    base_markup_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base markup percentage (e.g., 25.00 for 25%)"
    )
    volatility_adjustment = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Additional markup for volatile products (e.g., 10.00 for +10%)"
    )
    minimum_margin_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum margin to maintain (e.g., 15.00 for 15%)"
    )
    
    # Product category specific adjustments
    category_adjustments = models.JSONField(
        default=dict,
        help_text="Category-specific markup adjustments (e.g., {'vegetables': 20, 'fruits': 30})"
    )
    
    # Seasonal and trend adjustments
    trend_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Multiplier for trending products (e.g., 1.20 for +20%)"
    )
    seasonal_adjustment = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Seasonal price adjustment percentage"
    )
    
    # Rule status and validity
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this pricing rule is currently active"
    )
    effective_from = models.DateField(
        help_text="Date from which this rule becomes effective"
    )
    effective_until = models.DateField(
        null=True,
        blank=True,
        help_text="Date until which this rule is effective (null = indefinite)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'inventory_pricing_rule'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer_segment', 'is_active']),
            models.Index(fields=['effective_from', 'effective_until']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.customer_segment}) - {self.base_markup_percentage}%"
    
    def is_effective(self, date=None):
        """Check if the rule is effective on a given date"""
        if date is None:
            from datetime import date as dt
            date = dt.today()
        
        if not self.is_active:
            return False
        
        if date < self.effective_from:
            return False
        
        if self.effective_until and date > self.effective_until:
            return False
        
        return True
    
    def calculate_markup(self, product, market_price, volatility_level='stable'):
        """Calculate the final markup for a product based on this rule"""
        base_markup = self.base_markup_percentage
        
        # Add volatility adjustment
        if volatility_level in ['volatile', 'rising']:
            base_markup += self.volatility_adjustment
        
        # Add category-specific adjustment
        if hasattr(product, 'department') and product.department:
            category_name = product.department.name.lower()
            category_adjustment = self.category_adjustments.get(category_name, 0)
            base_markup += Decimal(str(category_adjustment))
        
        # Apply trend multiplier
        final_markup = base_markup * self.trend_multiplier
        
        # Add seasonal adjustment
        final_markup += self.seasonal_adjustment
        
        # Ensure minimum margin
        if final_markup < self.minimum_margin_percentage:
            final_markup = self.minimum_margin_percentage
        
        return final_markup


class CustomerPriceList(models.Model):
    """Generated price lists for customers based on market data and pricing rules"""
    
    # Customer and period information
    customer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        help_text="Customer this price list is for"
    )
    pricing_rule = models.ForeignKey(
        PricingRule,
        on_delete=models.CASCADE,
        help_text="Pricing rule used to generate this list"
    )
    
    # Price list metadata
    list_name = models.CharField(
        max_length=200,
        help_text="Name of the price list (e.g., 'Weekly Price List - 2023-09-11')"
    )
    effective_from = models.DateField(
        help_text="Date from which these prices are effective"
    )
    effective_until = models.DateField(
        help_text="Date until which these prices are effective"
    )
    
    # Generation information
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='generated_price_lists'
    )
    
    # Market data source
    based_on_market_data = models.DateField(
        help_text="Date of market data this price list is based on"
    )
    market_data_source = models.CharField(
        max_length=100,
        default="Tshwane Market",
        help_text="Source of market data (e.g., 'Tshwane Market')"
    )
    
    # Price list statistics
    total_products = models.IntegerField(
        default=0,
        help_text="Total number of products in this price list"
    )
    average_markup_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Average markup percentage across all products"
    )
    total_list_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total value of all products in the price list"
    )
    
    # Status and delivery
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('sent', 'Sent to Customer'),
        ('acknowledged', 'Acknowledged by Customer'),
        ('active', 'Active'),
        ('expired', 'Expired')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Notes and comments
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this price list"
    )
    
    class Meta:
        db_table = 'inventory_customer_price_list'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['customer', 'effective_from']),
            models.Index(fields=['status', 'effective_from']),
            models.Index(fields=['generated_at']),
        ]
        unique_together = ['customer', 'effective_from']
    
    def __str__(self):
        return f"{self.list_name} - {self.customer.get_full_name()}"
    
    @property
    def is_current(self):
        """Check if this price list is currently effective"""
        from datetime import date
        today = date.today()
        return self.effective_from <= today <= self.effective_until
    
    @property
    def days_until_expiry(self):
        """Calculate days until this price list expires"""
        from datetime import date
        return (self.effective_until - date.today()).days
    
    def activate(self):
        """Activate this price list and deactivate others for the same customer"""
        # Deactivate other active price lists for this customer
        CustomerPriceList.objects.filter(
            customer=self.customer,
            status='active'
        ).update(status='expired')
        
        # Activate this price list
        self.status = 'active'
        self.save()


class CustomerPriceListItem(models.Model):
    """Individual product prices within a customer price list"""
    
    price_list = models.ForeignKey(
        CustomerPriceList,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE
    )
    
    # Market price information
    market_price_excl_vat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Market price excluding VAT"
    )
    market_price_incl_vat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Market price including VAT"
    )
    market_price_date = models.DateField(
        help_text="Date of the market price data"
    )
    
    # Calculated customer price
    markup_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Applied markup percentage"
    )
    customer_price_excl_vat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Customer price excluding VAT"
    )
    customer_price_incl_vat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Customer price including VAT"
    )
    
    # Price change tracking
    previous_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Previous customer price for comparison"
    )
    price_change_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Percentage change from previous price"
    )
    
    # Product metadata
    unit_of_measure = models.CharField(
        max_length=50,
        default="each",
        help_text="Unit of measurement"
    )
    product_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Product category for reporting"
    )
    
    # Pricing flags
    is_volatile = models.BooleanField(
        default=False,
        help_text="Whether this product has volatile pricing"
    )
    is_seasonal = models.BooleanField(
        default=False,
        help_text="Whether this product is seasonal"
    )
    is_premium = models.BooleanField(
        default=False,
        help_text="Whether this is a premium product"
    )
    
    class Meta:
        db_table = 'inventory_customer_price_list_item'
        ordering = ['product__name']
        indexes = [
            models.Index(fields=['price_list', 'product']),
            models.Index(fields=['is_volatile', 'price_change_percentage']),
        ]
        unique_together = ['price_list', 'product']
    
    def __str__(self):
        return f"{self.product.name} - R{self.customer_price_incl_vat} ({self.markup_percentage}%)"
    
    @property
    def margin_amount(self):
        """Calculate the margin amount"""
        return self.customer_price_excl_vat - self.market_price_excl_vat
    
    @property
    def is_price_increase(self):
        """Check if this represents a price increase"""
        return self.price_change_percentage > 0
    
    @property
    def is_significant_change(self):
        """Check if this is a significant price change (>10%)"""
        return abs(self.price_change_percentage) > 10


class WeeklyPriceReport(models.Model):
    """Comprehensive weekly reports on pricing, market changes, and customer impact"""
    
    # Report period
    report_week_start = models.DateField(
        help_text="Monday of the report week"
    )
    report_week_end = models.DateField(
        help_text="Sunday of the report week"
    )
    
    # Report metadata
    report_name = models.CharField(
        max_length=200,
        help_text="Name of the report (e.g., 'Weekly Price Report - Week 37, 2023')"
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Market data summary
    total_market_prices_analyzed = models.IntegerField(
        default=0,
        help_text="Total number of market prices analyzed"
    )
    average_market_volatility = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Average price volatility percentage"
    )
    most_volatile_product = models.CharField(
        max_length=200,
        blank=True,
        help_text="Product with highest price volatility"
    )
    most_volatile_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Highest volatility percentage"
    )
    
    # Customer pricing summary
    total_price_lists_generated = models.IntegerField(
        default=0,
        help_text="Number of customer price lists generated"
    )
    total_customers_affected = models.IntegerField(
        default=0,
        help_text="Number of customers with price changes"
    )
    average_price_increase = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Average price increase percentage"
    )
    
    # Procurement impact
    total_procurement_recommendations = models.IntegerField(
        default=0,
        help_text="Number of procurement recommendations generated"
    )
    estimated_procurement_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Estimated total procurement cost"
    )
    potential_savings_identified = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Potential savings identified through smart procurement"
    )
    
    # Key insights
    key_insights = models.JSONField(
        default=list,
        help_text="Key insights and recommendations from the analysis"
    )
    
    # Report status
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('distributed', 'Distributed'),
        ('archived', 'Archived')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='generating'
    )
    
    class Meta:
        db_table = 'inventory_weekly_price_report'
        ordering = ['-report_week_start']
        indexes = [
            models.Index(fields=['report_week_start', 'status']),
            models.Index(fields=['generated_at']),
        ]
        unique_together = ['report_week_start', 'report_week_end']
    
    def __str__(self):
        return f"{self.report_name} ({self.report_week_start} to {self.report_week_end})"
    
    @property
    def week_number(self):
        """Get the ISO week number"""
        return self.report_week_start.isocalendar()[1]
    
    @property
    def year(self):
        """Get the year of the report"""
        return self.report_week_start.year


# Invoice Processing Models

class InvoicePhoto(models.Model):
    """Store uploaded invoice photos for processing"""
    
    # Basic info
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE)
    invoice_date = models.DateField()
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # File storage
    photo = models.ImageField(upload_to='invoices/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    # Processing status
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded - Awaiting Processing'),
        ('processing', 'Processing - OCR in Progress'),
        ('extracted', 'Data Extracted - Awaiting Weight Input'),
        ('completed', 'Completed - Ready for Stock Processing'),
        ('error', 'Error - Processing Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    
    # Metadata
    notes = models.TextField(blank=True, help_text="Additional notes about the invoice")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['supplier', 'invoice_date', 'original_filename']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.invoice_date} ({self.status})"


class SupplierProductMapping(models.Model):
    """Remember Karl's decisions on how supplier products map to our products"""
    
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE)
    supplier_product_code = models.CharField(max_length=100, blank=True)
    supplier_product_description = models.CharField(max_length=255)
    
    # Karl's mapping decision
    our_product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    
    # Pricing strategy Karl selected
    PRICING_STRATEGY_CHOICES = [
        ('per_kg', 'Price per kg (loose/bulk)'),
        ('per_package', 'Price per package (as delivered)'),
        ('per_unit', 'Price per unit (each, bunch, head)'),
        ('custom', 'Custom pricing calculation'),
    ]
    pricing_strategy = models.CharField(max_length=20, choices=PRICING_STRATEGY_CHOICES)
    
    # Additional context for pricing
    package_size_kg = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True,
        help_text="If per_package, what's the package size in kg?"
    )
    units_per_package = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="If per_unit, how many units per package?"
    )
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    notes = models.TextField(blank=True, help_text="Karl's notes about this mapping")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['supplier', 'supplier_product_code', 'supplier_product_description']
        ordering = ['supplier', 'supplier_product_description']
    
    def __str__(self):
        return f"{self.supplier.name}: {self.supplier_product_description} → {self.our_product.name} ({self.pricing_strategy})"


class ExtractedInvoiceData(models.Model):
    """Store extracted data from invoice photos before weight input"""
    
    invoice_photo = models.ForeignKey(InvoicePhoto, on_delete=models.CASCADE, related_name='extracted_items')
    
    # Extracted data
    line_number = models.PositiveIntegerField(help_text="Line number on invoice")
    product_code = models.CharField(max_length=100, blank=True, help_text="Supplier product code")
    product_description = models.CharField(max_length=255, help_text="Product description from invoice")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity from invoice")
    unit = models.CharField(max_length=50, help_text="Unit from invoice (bag, box, kg, etc)")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit")
    line_total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total for this line")
    
    # Weight input (to be added manually)
    actual_weight_kg = models.DecimalField(
        max_digits=10, decimal_places=2, 
        null=True, blank=True,
        help_text="Actual weight in kg (handwritten on invoice)"
    )
    
    # Karl's product matching decision
    supplier_mapping = models.ForeignKey(
        SupplierProductMapping,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Karl's mapping decision for this supplier product"
    )
    
    # Processing flags
    needs_weight_input = models.BooleanField(default=True)
    needs_product_matching = models.BooleanField(default=True)
    is_processed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['invoice_photo', 'line_number']
    
    def __str__(self):
        return f"{self.invoice_photo} - Line {self.line_number}: {self.product_description}"
    
    @property
    def calculated_price_per_kg(self):
        """Calculate price per kg if actual weight is provided"""
        if self.actual_weight_kg and self.actual_weight_kg > 0:
            return self.line_total / self.actual_weight_kg
        return None
    
    @property
    def final_unit_price(self):
        """Calculate final unit price based on Karl's pricing strategy"""
        if not self.supplier_mapping or not self.actual_weight_kg:
            return None
            
        strategy = self.supplier_mapping.pricing_strategy
        
        if strategy == 'per_kg':
            # Price per kg (loose/bulk)
            return self.line_total / self.actual_weight_kg
            
        elif strategy == 'per_package':
            # Price per package (as delivered)
            return self.unit_price
            
        elif strategy == 'per_unit':
            # Price per unit (need to calculate based on units per package)
            if self.supplier_mapping.units_per_package:
                return self.unit_price / self.supplier_mapping.units_per_package
            return None
            
        return None


# Import price validation models
from .models_price_validation import PriceHistory, PriceValidationResult, validate_price
