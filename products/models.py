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

class Product(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('piece', 'Piece'),
        ('box', 'Box'),
        ('punnet', 'Punnet'),
        ('bag', 'Bag'),
        ('bunch', 'Bunch'),
        ('head', 'Head'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    stock_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    needs_setup = models.BooleanField(default=False, help_text="Product was auto-created and needs pricing/inventory setup")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - R{self.price}/{self.unit}"
    
    class Meta:
        ordering = ['department__name', 'name']
        unique_together = ['name', 'department']

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

class Recipe(models.Model):
    """Recipe/ingredient breakdown for complex products"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='product_recipe')
    ingredients = models.JSONField(default=list, help_text="List of ingredient items with quantities")
    instructions = models.TextField(blank=True)
    prep_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    yield_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    yield_unit = models.CharField(max_length=20, choices=Product.UNIT_CHOICES, default='piece')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Recipe for {self.product.name}"
    
    class Meta:
        ordering = ['product__name']