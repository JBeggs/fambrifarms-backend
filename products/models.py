from django.db import models
from django.core.validators import MinValueValidator

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#16a34a', help_text='Hex color code (e.g. #16a34a)')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=50, default='kg')  # Simplified: kg, bunch, piece
    is_active = models.BooleanField(default=True)
    
    # AI parsing helpers
    common_names = models.JSONField(default=list, blank=True, help_text='Alternative names for AI parsing: ["onions", "red onions", "onion"]')
    typical_order_quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1, help_text='Typical restaurant order quantity')
    
    # Stock info
    in_stock = models.BooleanField(default=True)
    stock_level = models.CharField(max_length=20, choices=[
        ('high', 'High Stock'),
        ('medium', 'Medium Stock'), 
        ('low', 'Low Stock'),
        ('out', 'Out of Stock'),
    ], default='medium')
    
    def __str__(self):
        return f"{self.name} - R{self.price}/{self.unit}"


# CMS Models for Content Management
class CompanyInfo(models.Model):
    name = models.CharField(max_length=100, default="Fambri Farms")
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    phone_primary = models.CharField(max_length=20)
    phone_secondary = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    address = models.TextField()
    whatsapp = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Information"
        verbose_name_plural = "Company Information"

    def __str__(self):
        return self.name


class PageContent(models.Model):
    PAGE_CHOICES = [
        ('home', 'Homepage'),
        ('about', 'About Page'),
        ('contact', 'Contact Page'),
        ('departments', 'Departments Page'),
        ('products', 'Products Page'),
    ]
    
    page = models.CharField(max_length=20, choices=PAGE_CHOICES, unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    hero_title = models.CharField(max_length=200, blank=True)
    hero_subtitle = models.CharField(max_length=300, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Page Content"
        verbose_name_plural = "Page Contents"

    def __str__(self):
        return f"{self.get_page_display()} - {self.title}"


class BusinessHours(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    day = models.CharField(max_length=10, choices=DAY_CHOICES, unique=True)
    is_open = models.BooleanField(default=True)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    special_note = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = "Business Hours"
        verbose_name_plural = "Business Hours"
        ordering = ['day']

    def __str__(self):
        if self.is_open:
            return f"{self.get_day_display()}: {self.open_time} - {self.close_time}"
        else:
            return f"{self.get_day_display()}: Closed"


class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    image = models.ImageField(upload_to='team/', blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Team Member"
        verbose_name_plural = "Team Members"
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} - {self.position}"


class FAQ(models.Model):
    question = models.CharField(max_length=200)
    answer = models.TextField()
    category = models.CharField(max_length=50, default='general')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['order', 'question']

    def __str__(self):
        return self.question


class Testimonial(models.Model):
    customer_name = models.CharField(max_length=100)
    restaurant_name = models.CharField(max_length=100)
    content = models.TextField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} - {self.restaurant_name}"


# Import BusinessSettings from separate file to keep models organized
from .models_business_settings import BusinessSettings, DepartmentKeyword 