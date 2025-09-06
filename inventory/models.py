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
    is_weight = models.BooleanField(null=True, blank=True, help_text="True for weight-based, False for count-based")
    base_unit_multiplier = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="For conversion to base unit")
    is_active = models.BooleanField(null=True, blank=True)
    
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
    
    is_active = models.BooleanField(null=True, blank=True)
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
    
    is_active = models.BooleanField(null=True, blank=True)
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
        return (self.expiry_date - timezone.now().date()).days
    
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
    
    is_active = models.BooleanField(null=True, blank=True)
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
        return self.available_quantity + self.reserved_quantity
    
    @property
    def needs_production(self):
        """Check if production is needed"""
        return self.available_quantity <= self.reorder_level
    
    def reserve_stock(self, quantity):
        """Reserve stock for an order"""
        if self.available_quantity >= quantity:
            self.available_quantity -= quantity
            self.reserved_quantity += quantity
            self.save()
            return True
        return False
    
    def release_stock(self, quantity):
        """Release reserved stock (order cancelled)"""
        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
            self.available_quantity += quantity
            self.save()
            return True
        return False
    
    def sell_stock(self, quantity):
        """Sell reserved stock (order delivered)"""
        if self.reserved_quantity >= quantity:
            self.reserved_quantity -= quantity
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
        ('finished_adjust', 'Finished Inventory Adjustment'),
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
    is_active = models.BooleanField(null=True, blank=True)
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


# Import price validation models
from .models_price_validation import PriceHistory, PriceValidationResult, validate_price
