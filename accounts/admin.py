from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, RestaurantProfile

class RestaurantProfileInline(admin.StackedInline):
    model = RestaurantProfile
    can_delete = False
    verbose_name_plural = 'Restaurant Profile'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (RestaurantProfileInline,)
    
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_active', 'is_verified', 'date_joined')
    list_filter = ('user_type', 'is_active', 'is_verified', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Account Type', {'fields': ('user_type', 'is_verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'user_type'),
        }),
    )

@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'city', 'payment_terms', 'is_private_customer')
    list_filter = ('city', 'payment_terms', 'is_private_customer')
    search_fields = ('business_name', 'user__email', 'business_registration')
    readonly_fields = ('user',)
    fieldsets = (
        (None, {
            'fields': ('user', 'business_name', 'branch_name', 'is_private_customer')
        }),
        ('Contact Information', {
            'fields': ('address', 'city', 'postal_code')
        }),
        ('Business Details', {
            'fields': ('business_registration', 'payment_terms')
        }),
        ('WhatsApp Integration', {
            'fields': ('delivery_notes', 'order_pattern')
        }),
    ) 