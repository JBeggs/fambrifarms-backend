from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class SystemSetting(models.Model):
    """System-wide configuration settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default='general')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        ordering = ['category', 'key']

    def __str__(self):
        return f"{self.key}: {self.value}"


class CustomerSegment(models.Model):
    """Customer segment definitions"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    default_markup = models.DecimalField(max_digits=5, decimal_places=4, default=1.25)
    credit_limit_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    payment_terms_days = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_segments'
        ordering = ['name']

    def __str__(self):
        return self.name


class OrderStatus(models.Model):
    """Order status definitions"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    is_final = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_statuses'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.display_name


class StockAdjustmentType(models.Model):
    """Stock adjustment type definitions"""
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    affects_cost = models.BooleanField(default=False)
    requires_reason = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_adjustment_types'
        ordering = ['name']

    def __str__(self):
        return self.display_name


class BusinessConfiguration(models.Model):
    """Business configuration settings"""
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    value_type = models.CharField(max_length=20, choices=[
        ('decimal', 'Decimal'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('string', 'String'),
    ])
    decimal_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    integer_value = models.IntegerField(null=True, blank=True)
    boolean_value = models.BooleanField(null=True, blank=True)
    string_value = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default='general')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_configuration'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.display_name}: {self.get_value()}"

    def get_value(self):
        """Get the appropriate value based on type"""
        if self.value_type == 'decimal':
            return self.decimal_value
        elif self.value_type == 'integer':
            return self.integer_value
        elif self.value_type == 'boolean':
            return self.boolean_value
        else:
            return self.string_value

    def set_value(self, value):
        """Set the appropriate value based on type"""
        if self.value_type == 'decimal':
            self.decimal_value = value
        elif self.value_type == 'integer':
            self.integer_value = value
        elif self.value_type == 'boolean':
            self.boolean_value = value
        else:
            self.string_value = str(value)
