from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from datetime import timedelta
import statistics

class PriceHistory(models.Model):
    """
    Track historical prices for products and raw materials
    """
    # Item references - only one should be set
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_history'
    )
    raw_material = models.ForeignKey(
        'RawMaterial',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='price_history'
    )
    
    # Price details
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per unit"
    )
    
    unit = models.ForeignKey(
        'UnitOfMeasure',
        on_delete=models.PROTECT,
        help_text="Unit of measure for this price"
    )
    
    # Context
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Supplier who provided this price"
    )
    
    quantity_purchased = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity purchased at this price"
    )
    
    # Source of price data
    source_type = models.CharField(
        max_length=20,
        choices=[
            ('purchase_order', 'Purchase Order'),
            ('invoice', 'Invoice'),
            ('manual_entry', 'Manual Entry'),
            ('market_data', 'Market Data'),
        ]
    )
    
    source_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reference number (PO, Invoice, etc.)"
    )
    
    # Quality and conditions
    quality_grade = models.CharField(
        max_length=10,
        choices=[
            ('A', 'Grade A - Premium'),
            ('B', 'Grade B - Standard'),
            ('C', 'Grade C - Economy'),
            ('R', 'Grade R - Reject/Processing'),
        ]
    )
    
    # Timestamps
    price_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date when this price was effective"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Validation flags
    is_validated = models.BooleanField(
        default=False,
        help_text="Whether this price has been validated by a manager"
    )
    
    validation_notes = models.TextField(
        blank=True,
        help_text="Notes from price validation process"
    )
    
    class Meta:
        verbose_name = "Price History"
        verbose_name_plural = "Price History"
        ordering = ['-price_date']
        indexes = [
            models.Index(fields=['product', 'price_date']),
            models.Index(fields=['raw_material', 'price_date']),
            models.Index(fields=['supplier', 'price_date']),
        ]
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Ensure exactly one item is referenced
        if not (bool(self.product) ^ bool(self.raw_material)):
            raise ValidationError("Must reference exactly one product OR raw material")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def item_name(self):
        """Get the name of the item this price is for"""
        if self.product:
            return self.product.name
        elif self.raw_material:
            return self.raw_material.name
        return "Unknown"
    
    @property
    def item_type(self):
        """Get the type of item"""
        if self.product:
            return "Product"
        elif self.raw_material:
            return "Raw Material"
        return "Unknown"
    
    def __str__(self):
        return f"{self.item_name} - R{self.unit_price}/{self.unit.abbreviation} ({self.price_date.strftime('%Y-%m-%d')})"


class PriceValidationResult(models.Model):
    """
    Results of price validation checks
    """
    price_history = models.OneToOneField(
        PriceHistory,
        on_delete=models.CASCADE,
        related_name='validation_result'
    )
    
    # Validation metrics
    historical_average = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Average price over last 90 days"
    )
    
    variance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage variance from historical average"
    )
    
    # Validation status
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('within_range', 'Within Expected Range'),
            ('high_variance', 'High Variance - Review Required'),
            ('extreme_variance', 'Extreme Variance - Approval Required'),
            ('no_history', 'No Historical Data'),
            ('approved', 'Manually Approved'),
            ('rejected', 'Rejected'),
        ]
    )
    
    # Comparison data
    min_recent_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    max_recent_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    median_recent_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Validation details
    validation_date = models.DateTimeField(auto_now_add=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    validation_notes = models.TextField(
        blank=True,
        help_text="Notes from validation process"
    )
    
    class Meta:
        verbose_name = "Price Validation Result"
        verbose_name_plural = "Price Validation Results"
    
    def __str__(self):
        return f"{self.price_history.item_name} - {self.validation_status}"


def validate_price(item, unit_price, unit, supplier=None, quality_grade='B'):
    """
    Validate a price against historical data
    
    Args:
        item: Product or RawMaterial instance
        unit_price: Decimal price per unit
        unit: UnitOfMeasure instance
        supplier: Supplier instance (optional)
        quality_grade: Quality grade (A, B, C, R)
    
    Returns:
        dict with validation results
    """
    from products.models import BusinessSettings
    
    # Get business settings for variance thresholds
    settings = BusinessSettings.get_settings()
    max_variance = settings.max_price_variance_percent
    approval_threshold = settings.require_price_approval_above
    
    # Determine if this is a product or raw material
    is_product = hasattr(item, 'department')  # Products have departments
    
    # Get recent price history (last 90 days)
    cutoff_date = timezone.now() - timedelta(days=90)
    
    if is_product:
        recent_prices = PriceHistory.objects.filter(
            product=item,
            unit=unit,
            quality_grade=quality_grade,
            price_date__gte=cutoff_date,
            is_validated=True
        ).values_list('unit_price', flat=True)
    else:
        query = PriceHistory.objects.filter(
            raw_material=item,
            unit=unit,
            quality_grade=quality_grade,
            price_date__gte=cutoff_date,
            is_validated=True
        )
        
        # Filter by supplier if provided
        if supplier:
            query = query.filter(supplier=supplier)
        
        recent_prices = query.values_list('unit_price', flat=True)
    
    # Convert to list of Decimals
    recent_prices = [Decimal(str(price)) for price in recent_prices]
    
    result = {
        'status': 'within_range',
        'requires_approval': False,
        'historical_average': None,
        'variance_percentage': None,
        'min_recent_price': None,
        'max_recent_price': None,
        'median_recent_price': None,
        'message': 'Price is within expected range',
        'sample_size': len(recent_prices)
    }
    
    # Check if price requires approval due to amount
    if unit_price >= approval_threshold:
        result['requires_approval'] = True
        result['message'] = f'Price exceeds approval threshold of R{approval_threshold}'
    
    # If no historical data, mark as such
    if not recent_prices:
        result['status'] = 'no_history'
        result['message'] = 'No historical price data available for comparison'
        return result
    
    # Calculate statistics
    result['historical_average'] = Decimal(str(statistics.mean(recent_prices)))
    result['min_recent_price'] = min(recent_prices)
    result['max_recent_price'] = max(recent_prices)
    result['median_recent_price'] = Decimal(str(statistics.median(recent_prices)))
    
    # Calculate variance percentage
    if result['historical_average'] > 0:
        variance = ((unit_price - result['historical_average']) / result['historical_average']) * 100
        result['variance_percentage'] = Decimal(str(round(float(variance), 2)))
        
        # Determine validation status
        abs_variance = abs(result['variance_percentage'])
        
        if abs_variance <= max_variance:
            result['status'] = 'within_range'
            result['message'] = f'Price variance of {result["variance_percentage"]}% is within acceptable range'
        elif abs_variance <= (max_variance * 2):  # Double the threshold for extreme variance
            result['status'] = 'high_variance'
            result['requires_approval'] = True
            result['message'] = f'High price variance of {result["variance_percentage"]}% requires review'
        else:
            result['status'] = 'extreme_variance'
            result['requires_approval'] = True
            result['message'] = f'Extreme price variance of {result["variance_percentage"]}% requires manager approval'
    
    return result
