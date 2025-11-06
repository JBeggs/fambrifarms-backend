from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, RestaurantProfile, FarmProfile, PrivateCustomerProfile

class RestaurantProfileInline(admin.StackedInline):
    model = RestaurantProfile
    can_delete = False
    verbose_name_plural = 'Restaurant Profile'
    readonly_fields = ('created_at', 'updated_at')
    extra = 0

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (RestaurantProfileInline,)
    
    list_display = (
        'email_link', 'full_name', 'user_type_colored', 'phone', 
        'is_active_icon', 'is_verified_icon', 'order_count', 
        'last_login_formatted', 'date_joined_formatted'
    )
    list_filter = (
        'user_type', 'is_active', 'is_verified', 'is_staff', 'is_superuser',
        ('date_joined', admin.DateFieldListFilter),
        ('last_login', admin.DateFieldListFilter),
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'
    
    readonly_fields = ('date_joined', 'last_login', 'order_count', 'total_order_value')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('email', 'password')
        }),
        ('Personal Details', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Account Type & Status', {
            'fields': ('user_type', 'is_verified', 'roles', 'restaurant_roles')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Activity Summary', {
            'fields': ('order_count', 'total_order_value'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'user_type', 'phone'),
        }),
    )
    
    def email_link(self, obj):
        """Display email as clickable link to user detail"""
        return format_html(
            '<a href="{}" style="color: #0066cc; font-weight: bold;">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.pk]),
            obj.email
        )
    email_link.short_description = 'Email'
    email_link.admin_order_field = 'email'
    
    def full_name(self, obj):
        """Display full name or email if no name"""
        name = obj.get_full_name().strip()
        if name:
            return name
        return format_html('<em>{}</em>', obj.email.split('@')[0])
    full_name.short_description = 'Full Name'
    full_name.admin_order_field = 'first_name'
    
    def user_type_colored(self, obj):
        """Display user type with color coding"""
        colors = {
            'admin': '#dc3545',  # Red
            'farm_manager': '#fd7e14',  # Orange
            'staff': '#6f42c1',  # Purple
            'restaurant': '#28a745',  # Green
            'private': '#007bff',  # Blue
            'stock_taker': '#17a2b8',  # Teal
        }
        color = colors.get(obj.user_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_user_type_display()
        )
    user_type_colored.short_description = 'User Type'
    user_type_colored.admin_order_field = 'user_type'
    
    def is_active_icon(self, obj):
        """Display active status as icon"""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 14px;">✓ Active</span>')
        return format_html('<span style="color: red; font-size: 14px;">✗ Inactive</span>')
    is_active_icon.short_description = 'Status'
    is_active_icon.admin_order_field = 'is_active'
    
    def is_verified_icon(self, obj):
        """Display verified status as icon"""
        if obj.is_verified:
            return format_html('<span style="color: green; font-size: 12px;">✓ Verified</span>')
        return format_html('<span style="color: orange; font-size: 12px;">⚠ Unverified</span>')
    is_verified_icon.short_description = 'Verified'
    is_verified_icon.admin_order_field = 'is_verified'
    
    def last_login_formatted(self, obj):
        """Format last login date nicely"""
        if obj.last_login:
            return obj.last_login.strftime('%Y-%m-%d %H:%M')
        return format_html('<em>Never</em>')
    last_login_formatted.short_description = 'Last Login'
    last_login_formatted.admin_order_field = 'last_login'
    
    def date_joined_formatted(self, obj):
        """Format join date nicely"""
        return obj.date_joined.strftime('%Y-%m-%d %H:%M')
    date_joined_formatted.short_description = 'Date Joined'
    date_joined_formatted.admin_order_field = 'date_joined'
    
    def order_count(self, obj):
        """Display number of orders for this user"""
        count = obj.orders.count()
        if count > 0:
            return format_html(
                '<a href="{}?restaurant__id__exact={}">{} orders</a>',
                reverse('admin:orders_order_changelist'),
                obj.pk,
                count
            )
        return '0 orders'
    order_count.short_description = 'Orders'
    
    def total_order_value(self, obj):
        """Display total value of all orders"""
        from django.db.models import Sum
        total = obj.orders.aggregate(total=Sum('total_amount'))['total']
        if total:
            return f'R{total:,.2f}'
        return 'R0.00'
    total_order_value.short_description = 'Total Order Value'

@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    list_display = (
        'business_name_link', 'user_email', 'branch_name', 'city', 
        'payment_terms', 'is_private_customer_icon', 'order_count',
        'created_at_formatted', 'updated_at_formatted'
    )
    list_filter = (
        'city', 'payment_terms', 'is_private_customer',
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'business_name', 'branch_name', 'user__email', 
        'business_registration', 'address', 'delivery_notes'
    )
    readonly_fields = ('user', 'created_at', 'updated_at', 'order_count', 'total_order_value')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Business Information', {
            'fields': ('user', 'business_name', 'branch_name', 'is_private_customer')
        }),
        ('Contact & Location', {
            'fields': ('address', 'city', 'postal_code')
        }),
        ('Business Details', {
            'fields': ('business_registration', 'payment_terms', 'preferred_pricing_rule')
        }),
        ('WhatsApp & Order Management', {
            'fields': ('delivery_notes', 'order_pattern'),
            'description': 'Special delivery requirements and typical order patterns from WhatsApp'
        }),
        ('Activity Summary', {
            'fields': ('order_count', 'total_order_value'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def business_name_link(self, obj):
        """Display business name as link with branch info"""
        name = obj.business_name
        if obj.branch_name:
            name = f"{name} - {obj.branch_name}"
        return format_html(
            '<a href="{}" style="color: #0066cc; font-weight: bold;">{}</a>',
            reverse('admin:accounts_restaurantprofile_change', args=[obj.pk]),
            name
        )
    business_name_link.short_description = 'Business Name'
    business_name_link.admin_order_field = 'business_name'
    
    def user_email(self, obj):
        """Display linked user email"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            obj.user.email
        )
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'
    
    def is_private_customer_icon(self, obj):
        """Display private customer status as icon"""
        if obj.is_private_customer:
            return format_html('<span style="color: blue; font-size: 12px;">👤 Private</span>')
        return format_html('<span style="color: green; font-size: 12px;">🏢 Business</span>')
    is_private_customer_icon.short_description = 'Type'
    is_private_customer_icon.admin_order_field = 'is_private_customer'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def updated_at_formatted(self, obj):
        """Format update date"""
        if obj.updated_at:
            return obj.updated_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    updated_at_formatted.short_description = 'Updated'
    updated_at_formatted.admin_order_field = 'updated_at'
    
    def order_count(self, obj):
        """Display number of orders"""
        count = obj.user.orders.count()
        if count > 0:
            return format_html(
                '<a href="{}?restaurant__id__exact={}">{}</a>',
                reverse('admin:orders_order_changelist'),
                obj.user.pk,
                count
            )
        return '0'
    order_count.short_description = 'Orders'
    
    def total_order_value(self, obj):
        """Display total order value"""
        from django.db.models import Sum
        total = obj.user.orders.aggregate(total=Sum('total_amount'))['total']
        if total:
            return f'R{total:,.2f}'
        return 'R0.00'
    total_order_value.short_description = 'Total Order Value'


@admin.register(FarmProfile)
class FarmProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_name', 'employee_id', 'position', 'department',
        'access_level_colored', 'permissions_summary', 
        'created_at_formatted', 'updated_at_formatted'
    )
    list_filter = (
        'access_level', 'department', 'position',
        'can_manage_inventory', 'can_approve_orders', 'can_manage_customers',
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'user__first_name', 'user__last_name', 'user__email',
        'employee_id', 'position', 'department', 'notes'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('user', 'employee_id', 'position', 'department')
        }),
        ('Contact Details', {
            'fields': ('whatsapp_number',)
        }),
        ('Access & Permissions', {
            'fields': (
                'access_level', 'can_manage_inventory', 'can_approve_orders', 
                'can_manage_customers', 'can_view_reports'
            )
        }),
        ('Additional Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_name(self, obj):
        """Display user full name with link"""
        name = obj.user.get_full_name() or obj.user.email
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            name
        )
    user_name.short_description = 'Staff Member'
    user_name.admin_order_field = 'user__first_name'
    
    def access_level_colored(self, obj):
        """Display access level with color coding"""
        colors = {
            'basic': '#28a745',    # Green
            'manager': '#fd7e14',  # Orange  
            'admin': '#dc3545',    # Red
        }
        color = colors.get(obj.access_level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_access_level_display()
        )
    access_level_colored.short_description = 'Access Level'
    access_level_colored.admin_order_field = 'access_level'
    
    def permissions_summary(self, obj):
        """Display summary of permissions"""
        perms = []
        if obj.can_manage_inventory:
            perms.append('📦 Inventory')
        if obj.can_approve_orders:
            perms.append('✅ Orders')
        if obj.can_manage_customers:
            perms.append('👥 Customers')
        if obj.can_view_reports:
            perms.append('📊 Reports')
        return format_html(' | '.join(perms)) if perms else '-'
    permissions_summary.short_description = 'Permissions'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def updated_at_formatted(self, obj):
        """Format update date"""
        if obj.updated_at:
            return obj.updated_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    updated_at_formatted.short_description = 'Updated'
    updated_at_formatted.admin_order_field = 'updated_at'


@admin.register(PrivateCustomerProfile)
class PrivateCustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user_name', 'customer_type_colored', 'city_from_address',
        'preferred_delivery_day', 'credit_limit', 'order_count',
        'created_at_formatted', 'updated_at_formatted'
    )
    list_filter = (
        'customer_type', 'preferred_delivery_day',
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'user__first_name', 'user__last_name', 'user__email',
        'delivery_address', 'whatsapp_number', 'order_notes'
    )
    readonly_fields = ('created_at', 'updated_at', 'order_count', 'total_order_value')
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user', 'customer_type')
        }),
        ('Delivery Details', {
            'fields': ('delivery_address', 'delivery_instructions', 'preferred_delivery_day')
        }),
        ('Contact & Financial', {
            'fields': ('whatsapp_number', 'credit_limit')
        }),
        ('Order Preferences', {
            'fields': ('order_notes',)
        }),
        ('Activity Summary', {
            'fields': ('order_count', 'total_order_value'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_name(self, obj):
        """Display user full name with link"""
        name = obj.user.get_full_name() or obj.user.email
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:accounts_user_change', args=[obj.user.pk]),
            name
        )
    user_name.short_description = 'Customer Name'
    user_name.admin_order_field = 'user__first_name'
    
    def customer_type_colored(self, obj):
        """Display customer type with color coding"""
        colors = {
            'household': '#28a745',      # Green
            'small_business': '#fd7e14', # Orange
            'personal': '#007bff',       # Blue
        }
        color = colors.get(obj.customer_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_customer_type_display()
        )
    customer_type_colored.short_description = 'Customer Type'
    customer_type_colored.admin_order_field = 'customer_type'
    
    def city_from_address(self, obj):
        """Extract city/area from delivery address"""
        # Simple extraction - could be improved with better parsing
        address_lines = obj.delivery_address.split('\n')
        if len(address_lines) > 1:
            return address_lines[-1].strip()  # Last line usually contains city
        return obj.delivery_address[:30] + '...' if len(obj.delivery_address) > 30 else obj.delivery_address
    city_from_address.short_description = 'Location'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def updated_at_formatted(self, obj):
        """Format update date"""
        if obj.updated_at:
            return obj.updated_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    updated_at_formatted.short_description = 'Updated'
    updated_at_formatted.admin_order_field = 'updated_at'
    
    def order_count(self, obj):
        """Display number of orders"""
        count = obj.user.orders.count()
        if count > 0:
            return format_html(
                '<a href="{}?restaurant__id__exact={}">{}</a>',
                reverse('admin:orders_order_changelist'),
                obj.user.pk,
                count
            )
        return '0'
    order_count.short_description = 'Orders'
    
    def total_order_value(self, obj):
        """Display total order value"""
        from django.db.models import Sum
        total = obj.user.orders.aggregate(total=Sum('total_amount'))['total']
        if total:
            return f'R{total:,.2f}'
        return 'R0.00'
    total_order_value.short_description = 'Total Order Value' 