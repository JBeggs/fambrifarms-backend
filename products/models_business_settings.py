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
    
    # App Configuration Settings
    django_base_url = models.URLField(
        default='http://127.0.0.1:8000/api',
        help_text="Base URL for Django API endpoints"
    )
    
    whatsapp_base_url = models.URLField(
        default='http://127.0.0.1:5001/api',
        help_text="Base URL for WhatsApp scraper API"
    )
    
    # Pricing Rule Defaults
    default_base_markup = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.25'),
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text="Default base markup multiplier for new pricing rules"
    )
    
    default_volatility_adjustment = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.15'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Default volatility adjustment for new pricing rules"
    )
    
    default_trend_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.10'),
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text="Default trend multiplier for new pricing rules"
    )
    
    # Customer Segments (JSON field for flexibility)
    customer_segments = models.JSONField(
        default=list,
        help_text="Available customer segments as JSON array (e.g., ['premium', 'standard', 'budget'])"
    )
    
    # API Configuration
    api_timeout_seconds = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        help_text="Default timeout for API requests in seconds"
    )
    
    max_retry_attempts = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Maximum number of retry attempts for failed API calls"
    )
    
    # Pagination Defaults
    default_messages_limit = models.IntegerField(
        default=100,
        validators=[MinValueValidator(10), MaxValueValidator(1000)],
        help_text="Default limit for messages API pagination"
    )
    
    default_stock_updates_limit = models.IntegerField(
        default=50,
        validators=[MinValueValidator(10), MaxValueValidator(500)],
        help_text="Default limit for stock updates API pagination"
    )
    
    # Procurement Buffer Settings
    default_spoilage_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal('0.15'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
        help_text="Default spoilage rate for new products (0.15 = 15%)"
    )
    
    default_cutting_waste_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal('0.10'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
        help_text="Default cutting waste rate for new products (0.10 = 10%)"
    )
    
    default_quality_rejection_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal('0.05'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('1'))],
        help_text="Default quality rejection rate for new products (0.05 = 5%)"
    )
    
    default_market_pack_size = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('5.0'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Default market pack size for new products"
    )
    
    default_peak_season_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.3'),
        validators=[MinValueValidator(Decimal('1.0'))],
        help_text="Default peak season buffer multiplier"
    )
    
    # Department-specific buffer settings (JSON for flexibility)
    department_buffer_settings = models.JSONField(
        default=dict,
        help_text="Department-specific buffer settings as JSON"
    )
    
    # Global procurement settings
    enable_seasonal_adjustments = models.BooleanField(
        default=True,
        help_text="Enable seasonal buffer adjustments"
    )
    
    auto_create_buffers = models.BooleanField(
        default=True,
        help_text="Automatically create procurement buffers for new products"
    )
    
    buffer_calculation_method = models.CharField(
        max_length=20,
        choices=[
            ('additive', 'Additive (sum all rates)'),
            ('multiplicative', 'Multiplicative (compound rates)'),
        ],
        default='additive',
        help_text="Method for calculating total buffer rates"
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
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'customer_segments': ['premium', 'standard', 'budget'],
                'department_buffer_settings': {
                    'Vegetables': {
                        'spoilage_rate': 0.15,
                        'cutting_waste_rate': 0.12,
                        'quality_rejection_rate': 0.08,
                        'market_pack_size': 5.0,
                        'market_pack_unit': 'kg',
                        'is_seasonal': True,
                        'peak_season_months': [11, 12, 1, 2, 3],
                        'peak_season_buffer_multiplier': 1.3
                    },
                    'Fruits': {
                        'spoilage_rate': 0.20,
                        'cutting_waste_rate': 0.08,
                        'quality_rejection_rate': 0.12,
                        'market_pack_size': 10.0,
                        'market_pack_unit': 'kg',
                        'is_seasonal': True,
                        'peak_season_months': [10, 11, 12, 1, 2],
                        'peak_season_buffer_multiplier': 1.4
                    },
                    'Herbs & Spices': {
                        'spoilage_rate': 0.08,
                        'cutting_waste_rate': 0.05,
                        'quality_rejection_rate': 0.03,
                        'market_pack_size': 1.0,
                        'market_pack_unit': 'kg',
                        'is_seasonal': False,
                        'peak_season_months': [],
                        'peak_season_buffer_multiplier': 1.0
                    },
                    'Mushrooms': {
                        'spoilage_rate': 0.25,
                        'cutting_waste_rate': 0.10,
                        'quality_rejection_rate': 0.15,
                        'market_pack_size': 2.5,
                        'market_pack_unit': 'kg',
                        'is_seasonal': False,
                        'peak_season_months': [],
                        'peak_season_buffer_multiplier': 1.0
                    }
                }
            }
        )
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
