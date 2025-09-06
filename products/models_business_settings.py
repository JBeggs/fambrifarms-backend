from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from decimal import Decimal

class BusinessSettings(models.Model):
    """
    Configurable business settings to replace hardcoded values
    This is a singleton model - only one instance should exist
    """
    
    # Inventory Defaults
    default_minimum_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Default minimum stock level for new products"
    )
    
    default_reorder_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Default reorder level for new products"
    )
    
    default_maximum_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Default maximum stock level for new products"
    )
    
    # Default quantities for order suggestions
    default_order_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Default quantity suggested when adding items to orders"
    )
    
    # Price Validation
    max_price_variance_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Maximum allowed price variance percentage from historical average"
    )
    
    require_price_approval_above = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('1000.00'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Require manager approval for prices above this amount"
    )
    
    # Inventory Tracking Requirements
    require_batch_tracking = models.BooleanField(
        default=True,
        help_text="Require batch/lot numbers for all inventory receipts"
    )
    
    require_expiry_dates = models.BooleanField(
        default=True,
        help_text="Require expiry dates for perishable goods"
    )
    
    require_quality_grades = models.BooleanField(
        default=True,
        help_text="Require quality grade selection (A, B, C, R) for received goods"
    )
    
    # Default Units
    default_weight_unit = models.ForeignKey(
        'inventory.UnitOfMeasure', 
        on_delete=models.PROTECT,
        related_name='business_settings_weight',
        null=True,
        blank=True,
        help_text="Default unit for weight-based products"
    )
    
    default_count_unit = models.ForeignKey(
        'inventory.UnitOfMeasure', 
        on_delete=models.PROTECT,
        related_name='business_settings_count',
        null=True,
        blank=True,
        help_text="Default unit for count-based products"
    )
    
    # Validation Rules
    min_phone_digits = models.IntegerField(
        default=10,
        validators=[MinValueValidator(8), MaxValueValidator(15)],
        help_text="Minimum number of digits required in phone numbers"
    )
    
    require_email_validation = models.BooleanField(
        default=True,
        help_text="Require valid email format for customer emails"
    )
    
    # Department Assignment
    auto_assign_department = models.BooleanField(
        default=False,
        help_text="Automatically assign products to departments based on keywords"
    )
    
    default_department = models.ForeignKey(
        'products.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default department for new products when auto-assignment is disabled"
    )
    
    # Supplier Management
    default_supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default supplier for new raw materials"
    )
    
    # System Behavior
    allow_negative_inventory = models.BooleanField(
        default=False,
        help_text="Allow inventory levels to go negative (overselling)"
    )
    
    auto_create_purchase_orders = models.BooleanField(
        default=False,
        help_text="Automatically create purchase orders when stock falls below reorder level"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Last user to update these settings"
    )
    
    class Meta:
        verbose_name = "Business Settings"
        verbose_name_plural = "Business Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists (singleton pattern)
        if not self.pk and BusinessSettings.objects.exists():
            raise ValueError("Only one BusinessSettings instance is allowed. Update the existing one.")
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Get the business settings instance, creating with defaults if none exists"""
        settings, created = cls.objects.get_or_create(pk=1)
        if created:
            print("Created new BusinessSettings with default values")
        return settings
    
    def __str__(self):
        return f"Business Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"


class DepartmentKeyword(models.Model):
    """
    Keywords for automatic department assignment
    """
    department = models.ForeignKey(
        'products.Department',
        on_delete=models.CASCADE,
        related_name='keywords'
    )
    
    keyword = models.CharField(
        max_length=50,
        help_text="Keyword to match in product names for automatic department assignment"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['department', 'keyword']
        verbose_name = "Department Keyword"
        verbose_name_plural = "Department Keywords"
    
    def __str__(self):
        return f"{self.department.name}: {self.keyword}"
