from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    
    USER_TYPES = [
        ('restaurant', 'Restaurant'),
        ('private', 'Private Customer'),
        ('farm_manager', 'Farm Manager'),
        ('stock_taker', 'Stock Taker'),
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    ]
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='restaurant')
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)
    roles = models.JSONField(default=list, blank=True)
    restaurant_roles = models.JSONField(default=list, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"

class RestaurantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    business_name = models.CharField(max_length=200)
    branch_name = models.CharField(max_length=200, blank=True, help_text="Branch name for multi-location businesses (e.g., 'Debonairs Sandton')")
    business_registration = models.CharField(max_length=100, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    payment_terms = models.CharField(max_length=50, default='Net 30', blank=True)
    is_private_customer = models.BooleanField(default=False, help_text="Check if this is a private customer (individual) rather than a business")
    delivery_notes = models.TextField(blank=True, help_text="Special delivery requirements and notes from WhatsApp orders")
    order_pattern = models.CharField(max_length=200, blank=True, help_text="Typical order pattern (e.g., 'Tuesday orders - Italian restaurant supplies')")
    
    # Pricing configuration
    preferred_pricing_rule = models.ForeignKey(
        'inventory.PricingRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Override automatic pricing rule selection with a specific rule"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        if self.branch_name:
            return f"{self.business_name} - {self.branch_name}"
        return self.business_name

class FarmProfile(models.Model):
    """Profile for farm staff - managers, stock takers, etc."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100, blank=True, help_text="e.g., Operations, Inventory, Sales")
    position = models.CharField(max_length=100, blank=True, help_text="e.g., Farm Manager, Stock Taker")
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text="WhatsApp contact number")
    access_level = models.CharField(max_length=20, choices=[
        ('basic', 'Basic Access'),
        ('manager', 'Manager Access'), 
        ('admin', 'Admin Access'),
    ], default='basic')
    can_manage_inventory = models.BooleanField(default=False)
    can_approve_orders = models.BooleanField(default=False)
    can_manage_customers = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Additional notes about role and responsibilities")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.position}"
    
    class Meta:
        ordering = ['position', 'user__first_name']

class PrivateCustomerProfile(models.Model):
    """Profile for private customers like Sylvia, Marco, Arthur"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    customer_type = models.CharField(max_length=20, choices=[
        ('household', 'Household'),
        ('small_business', 'Small Business'),
        ('personal', 'Personal'),
    ], default='household')
    delivery_address = models.TextField()
    delivery_instructions = models.TextField(blank=True)
    preferred_delivery_day = models.CharField(max_length=20, choices=[
        ('tuesday', 'Tuesday'),
        ('thursday', 'Thursday'),
        ('any', 'Any Day'),
    ], default='tuesday')
    whatsapp_number = models.CharField(max_length=20, blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    order_notes = models.TextField(blank=True, help_text="Typical order patterns and preferences")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_customer_type_display()}"
    
    class Meta:
        ordering = ['user__first_name']