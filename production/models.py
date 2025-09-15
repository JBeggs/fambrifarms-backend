from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone

class Recipe(models.Model):
    """
    Production recipes for creating finished products from raw materials
    """
    product = models.OneToOneField('products.Product', on_delete=models.CASCADE, related_name='recipe')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Production details
    batch_size = models.PositiveIntegerField(default=1, help_text="Standard batch size")
    production_time_minutes = models.PositiveIntegerField(default=60)
    yield_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, 
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=10, default='1.0', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['product__name']
        
    def __str__(self):
        return f"Recipe: {self.product.name} (v{self.version})"

class RecipeIngredient(models.Model):
    """
    Raw materials/ingredients required for a recipe
    """
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='ingredients')
    raw_material = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='used_in_recipes')
    
    # Quantity required
    quantity = models.DecimalField(
        max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    unit = models.CharField(max_length=20, null=True, blank=True)
    
    # Optional details
    preparation_notes = models.TextField(blank=True)
    is_optional = models.BooleanField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['recipe', 'raw_material']
        ordering = ['raw_material__name']
        
    def __str__(self):
        return f"{self.raw_material.name} ({self.quantity} {self.unit})"

class ProductionBatch(models.Model):
    """
    Individual production runs/batches
    """
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic info
    batch_number = models.CharField(max_length=50, unique=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='production_batches')
    
    # Quantities
    planned_quantity = models.PositiveIntegerField()
    actual_quantity = models.PositiveIntegerField(null=True, blank=True)
    
    # Status and timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    planned_start_date = models.DateTimeField()
    planned_end_date = models.DateTimeField()
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    
    # Staff and notes
    produced_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    quality_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-planned_start_date']
        
    def __str__(self):
        return f"Batch {self.batch_number} - {self.recipe.product.name}"
    
    def save(self, *args, **kwargs):
        if not self.batch_number:
            # Generate batch number
            today = timezone.now().date()
            last_batch = ProductionBatch.objects.filter(
                batch_number__startswith=f"B{today.strftime('%Y%m%d')}"
            ).order_by('-batch_number').first()
            
            if last_batch:
                last_num = int(last_batch.batch_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.batch_number = f"B{today.strftime('%Y%m%d')}-{new_num:03d}"
        
        super().save(*args, **kwargs)
    
    @property
    def yield_percentage(self):
        if self.planned_quantity > 0:
            return (self.actual_quantity / self.planned_quantity) * 100
        return 0

class ProductionReservation(models.Model):
    """
    Reservations of raw materials for production batches
    """
    batch = models.ForeignKey(ProductionBatch, on_delete=models.CASCADE, related_name='reservations')
    raw_material = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Quantities
    quantity_reserved = models.DecimalField(
        max_digits=10, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    quantity_used = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.000'))]
    )
    
    # Status
    is_consumed = models.BooleanField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['batch', 'raw_material']
        ordering = ['raw_material__name']
        
    def __str__(self):
        return f"{self.raw_material.name} reserved for {self.batch.batch_number}"
    
    @property
    def quantity_remaining(self):
        return self.quantity_reserved - self.quantity_used

class QualityCheck(models.Model):
    """
    Quality control checks for production batches
    """
    RESULT_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('conditional', 'Conditional Pass'),
    ]
    
    batch = models.ForeignKey(ProductionBatch, on_delete=models.CASCADE, related_name='quality_checks')
    check_type = models.CharField(max_length=50)
    
    # Results
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    score = models.DecimalField(
        max_digits=5, decimal_places=2, 
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Details
    notes = models.TextField(blank=True)
    checked_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    check_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-check_date']
        
    def __str__(self):
        return f"{self.check_type} - {self.result} ({self.batch.batch_number})"