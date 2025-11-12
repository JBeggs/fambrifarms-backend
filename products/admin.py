from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Sum, Count
from .models import Department, Product, ProductAlert, Recipe, MarketProcurementRecommendation, MarketProcurementItem

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        'name_link', 'product_count', 'is_active_icon', 'description_preview',
        'created_at_formatted'
    )
    list_filter = (
        'is_active',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'product_count')
    
    fieldsets = (
        ('Department Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Statistics', {
            'fields': ('product_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def name_link(self, obj):
        """Display department name as link"""
        return format_html(
            '<a href="{}" style="color: #0066cc; font-weight: bold;">{}</a>',
            reverse('admin:products_department_change', args=[obj.pk]),
            obj.name
        )
    name_link.short_description = 'Department Name'
    name_link.admin_order_field = 'name'
    
    def is_active_icon(self, obj):
        """Display active status as icon"""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 14px;">✓ Active</span>')
        return format_html('<span style="color: red; font-size: 14px;">✗ Inactive</span>')
    is_active_icon.short_description = 'Status'
    is_active_icon.admin_order_field = 'is_active'
    
    def description_preview(self, obj):
        """Display truncated description"""
        if obj.description:
            preview = obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
            return format_html('<em>{}</em>', preview)
        return '-'
    description_preview.short_description = 'Description'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def product_count(self, obj):
        """Display number of products in department"""
        count = obj.products.count()
        if count > 0:
            return format_html(
                '<a href="{}?department__id__exact={}">{} products</a>',
                reverse('admin:products_product_changelist'),
                obj.pk,
                count
            )
        return '0 products'
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name_link', 'department_link', 'price', 'unit',
        'stock_status', 'needs_setup', 'is_active', 'supplier_info',
        'created_at_formatted', 'updated_at_formatted'
    )
    list_filter = (
        'department', 'unit', 'is_active', 'needs_setup',
        'procurement_supplier', 'cost_unit',
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
        ('last_cost_update', admin.DateFieldListFilter),
    )
    search_fields = (
        'name', 'description', 'department__name',
        'procurement_supplier__name', 'last_supplier__name'
    )
    readonly_fields = (
        'created_at', 'updated_at', 'order_count', 'total_order_value',
        'average_order_quantity', 'last_ordered_date'
    )
    date_hierarchy = 'created_at'
    list_editable = ('price', 'needs_setup', 'is_active')
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'description', 'department')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'unit', 'stock_level', 'minimum_stock', 'is_active', 'unlimited_stock')
        }),
        ('Procurement Management', {
            'fields': (
                'procurement_supplier', 'supplier_cost', 'cost_unit',
                'last_supplier', 'last_cost_update'
            ),
            'classes': ('collapse',),
            'description': 'Supplier and cost information for market procurement'
        }),
        ('Status Flags', {
            'fields': ('needs_setup',),
            'description': 'Product was auto-created and needs pricing/inventory setup'
        }),
        ('Activity Summary', {
            'fields': ('order_count', 'total_order_value', 'average_order_quantity', 'last_ordered_date'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_link(self, obj):
        """Display product name as link"""
        return format_html(
            '<a href="{}" style="color: #0066cc; font-weight: bold;">{}</a>',
            reverse('admin:products_product_change', args=[obj.pk]),
            obj.name
        )
    name_link.short_description = 'Product Name'
    name_link.admin_order_field = 'name'
    
    def department_link(self, obj):
        """Display department as link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:products_department_change', args=[obj.department.pk]),
            obj.department.name
        )
    department_link.short_description = 'Department'
    department_link.admin_order_field = 'department__name'
    
    def price_formatted(self, obj):
        """Display price with currency"""
        return f'R{obj.price}'
    price_formatted.short_description = 'Price'
    price_formatted.admin_order_field = 'price'
    
    def stock_status(self, obj):
        """Display stock level with status indicator"""
        if obj.stock_level <= obj.minimum_stock:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} {} (⚠ Low)</span>',
                obj.stock_level, obj.unit
            )
        elif obj.stock_level <= obj.minimum_stock * 2:
            return format_html(
                '<span style="color: orange;">{} {} (⚠ Getting Low)</span>',
                obj.stock_level, obj.unit
            )
        return format_html(
            '<span style="color: green;">{} {} (✓ OK)</span>',
            obj.stock_level, obj.unit
        )
    stock_status.short_description = 'Stock Status'
    stock_status.admin_order_field = 'stock_level'
    
    def needs_setup_icon(self, obj):
        """Display setup status"""
        if obj.needs_setup:
            return format_html(
                '<span style="color: orange; font-size: 12px;">⚠ Needs Setup</span>'
            )
        return format_html('<span style="color: green; font-size: 12px;">✓ Ready</span>')
    needs_setup_icon.short_description = 'Setup Status'
    needs_setup_icon.admin_order_field = 'needs_setup'
    
    def supplier_info(self, obj):
        """Display supplier information"""
        if obj.procurement_supplier:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:suppliers_supplier_change', args=[obj.procurement_supplier.pk]),
                obj.procurement_supplier.name[:20]
            )
        return format_html('<em>No supplier</em>')
    supplier_info.short_description = 'Primary Supplier'
    supplier_info.admin_order_field = 'procurement_supplier__name'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def updated_at_formatted(self, obj):
        """Format update date"""
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    updated_at_formatted.short_description = 'Updated'
    updated_at_formatted.admin_order_field = 'updated_at'
    
    def order_count(self, obj):
        """Display number of orders containing this product"""
        count = obj.orderitem_set.count()
        if count > 0:
            return format_html(
                '<a href="{}?product__id__exact={}">{} orders</a>',
                reverse('admin:orders_orderitem_changelist'),
                obj.pk,
                count
            )
        return '0 orders'
    order_count.short_description = 'Order Count'
    
    def total_order_value(self, obj):
        """Display total value of orders for this product"""
        total = obj.orderitem_set.aggregate(total=Sum('total_price'))['total']
        if total:
            return f'R{total:,.2f}'
        return 'R0.00'
    total_order_value.short_description = 'Total Order Value'
    
    def average_order_quantity(self, obj):
        """Display average quantity ordered"""
        from django.db.models import Avg
        avg = obj.orderitem_set.aggregate(avg=Avg('quantity'))['avg']
        if avg:
            return f'{avg:.2f} {obj.unit}'
        return f'0 {obj.unit}'
    average_order_quantity.short_description = 'Avg Order Qty'
    
    def last_ordered_date(self, obj):
        """Display last order date"""
        last_item = obj.orderitem_set.select_related('order').order_by('-order__created_at').first()
        if last_item:
            return last_item.order.created_at.strftime('%Y-%m-%d')
        return 'Never ordered'
    last_ordered_date.short_description = 'Last Ordered'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department', 'procurement_supplier', 'last_supplier')


@admin.register(ProductAlert)
class ProductAlertAdmin(admin.ModelAdmin):
    list_display = (
        'product_link', 'alert_type_colored', 'message_preview',
        'is_resolved_icon', 'created_by_order', 'resolved_by_link',
        'created_at_formatted', 'resolved_at_formatted'
    )
    list_filter = (
        'alert_type', 'is_resolved',
        ('created_at', admin.DateFieldListFilter),
        ('resolved_at', admin.DateFieldListFilter),
        'product__department',
    )
    search_fields = (
        'product__name', 'message', 'created_by_order',
        'product__department__name'
    )
    readonly_fields = ('created_at', 'resolved_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('product', 'alert_type', 'message')
        }),
        ('Context', {
            'fields': ('created_by_order',)
        }),
        ('Resolution', {
            'fields': ('is_resolved', 'resolved_by', 'resolved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def product_link(self, obj):
        """Display product as link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:products_product_change', args=[obj.product.pk]),
            obj.product.name
        )
    product_link.short_description = 'Product'
    product_link.admin_order_field = 'product__name'
    
    def alert_type_colored(self, obj):
        """Display alert type with color coding"""
        colors = {
            'needs_setup': '#fd7e14',    # Orange
            'low_stock': '#dc3545',      # Red
            'no_price': '#6f42c1',       # Purple
            'missing_recipe': '#20c997',  # Teal
        }
        color = colors.get(obj.alert_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_alert_type_display()
        )
    alert_type_colored.short_description = 'Alert Type'
    alert_type_colored.admin_order_field = 'alert_type'
    
    def message_preview(self, obj):
        """Display truncated message"""
        preview = obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
        return format_html('<em>{}</em>', preview)
    message_preview.short_description = 'Message'
    
    def is_resolved_icon(self, obj):
        """Display resolved status"""
        if obj.is_resolved:
            return format_html('<span style="color: green; font-size: 14px;">✓ Resolved</span>')
        return format_html('<span style="color: red; font-size: 14px;">⚠ Open</span>')
    is_resolved_icon.short_description = 'Status'
    is_resolved_icon.admin_order_field = 'is_resolved'
    
    def resolved_by_link(self, obj):
        """Display resolver as link"""
        if obj.resolved_by:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:accounts_user_change', args=[obj.resolved_by.pk]),
                obj.resolved_by.get_full_name() or obj.resolved_by.email
            )
        return '-'
    resolved_by_link.short_description = 'Resolved By'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def resolved_at_formatted(self, obj):
        """Format resolution date"""
        if obj.resolved_at:
            return obj.resolved_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    resolved_at_formatted.short_description = 'Resolved'
    resolved_at_formatted.admin_order_field = 'resolved_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'resolved_by', 'product__department')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'product_link', 'prep_time_formatted', 'yield_info',
        'ingredient_count', 'created_at_formatted', 'updated_at_formatted'
    )
    list_filter = (
        'product__department',
        ('created_at', admin.DateFieldListFilter),
        ('updated_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'product__name', 'instructions', 'product__department__name'
    )
    readonly_fields = ('created_at', 'updated_at', 'ingredient_count', 'estimated_cost')
    
    fieldsets = (
        ('Recipe Information', {
            'fields': ('product', 'instructions')
        }),
        ('Production Details', {
            'fields': ('prep_time_minutes', 'yield_quantity', 'yield_unit')
        }),
        ('Statistics', {
            'fields': ('ingredient_count', 'estimated_cost'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def product_link(self, obj):
        """Display product as link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:products_product_change', args=[obj.product.pk]),
            obj.product.name
        )
    product_link.short_description = 'Product'
    product_link.admin_order_field = 'product__name'
    
    def prep_time_formatted(self, obj):
        """Format preparation time"""
        hours = obj.prep_time_minutes // 60
        minutes = obj.prep_time_minutes % 60
        if hours > 0:
            return f'{hours}h {minutes}m'
        return f'{minutes}m'
    prep_time_formatted.short_description = 'Prep Time'
    prep_time_formatted.admin_order_field = 'prep_time_minutes'
    
    def yield_info(self, obj):
        """Display yield information"""
        return f'{obj.yield_quantity} {obj.yield_unit}'
    yield_info.short_description = 'Yield'
    yield_info.admin_order_field = 'yield_quantity'
    
    def ingredient_count(self, obj):
        """Display number of ingredients"""
        count = len(obj.ingredients)
        return f'{count} ingredients'
    ingredient_count.short_description = 'Ingredients'
    
    def estimated_cost(self, obj):
        """Display estimated cost"""
        # This would need to be calculated based on ingredient costs
        # For now, return placeholder
        return 'R0.00 (TBD)'
    estimated_cost.short_description = 'Estimated Cost'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def updated_at_formatted(self, obj):
        """Format update date"""
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    updated_at_formatted.short_description = 'Updated'
    updated_at_formatted.admin_order_field = 'updated_at'


class MarketProcurementItemInline(admin.TabularInline):
    model = MarketProcurementItem
    extra = 0
    fields = ('product', 'needed_quantity', 'recommended_quantity', 'estimated_unit_price', 'estimated_total_cost', 'priority')
    readonly_fields = ('estimated_total_cost',)


@admin.register(MarketProcurementRecommendation)
class MarketProcurementRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        'for_date', 'status_colored', 'item_count', 'total_cost_formatted',
        'approved_by_link', 'created_at_formatted', 'approved_at_formatted'
    )
    list_filter = (
        'status',
        ('for_date', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        ('approved_at', admin.DateFieldListFilter),
    )
    search_fields = ('notes', 'approved_by__email')
    readonly_fields = ('created_at', 'approved_at', 'item_count', 'total_estimated_cost')
    date_hierarchy = 'for_date'
    inlines = [MarketProcurementItemInline]
    
    fieldsets = (
        ('Recommendation Details', {
            'fields': ('for_date', 'status', 'total_estimated_cost')
        }),
        ('Analysis Data', {
            'fields': ('analysis_data',),
            'classes': ('collapse',)
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_at', 'notes')
        }),
        ('Statistics', {
            'fields': ('item_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def status_colored(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#fd7e14',    # Orange
            'approved': '#28a745',   # Green
            'purchased': '#007bff',  # Blue
            'cancelled': '#dc3545',  # Red
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    def item_count(self, obj):
        """Display number of items in recommendation"""
        count = obj.items.count()
        if count > 0:
            return format_html(
                '<a href="{}?recommendation__id__exact={}">{} items</a>',
                reverse('admin:products_marketprocurementitem_changelist'),
                obj.pk,
                count
            )
        return '0 items'
    item_count.short_description = 'Items'
    
    def total_cost_formatted(self, obj):
        """Format total cost"""
        return f'R{obj.total_estimated_cost:,.2f}'
    total_cost_formatted.short_description = 'Total Cost'
    total_cost_formatted.admin_order_field = 'total_estimated_cost'
    
    def approved_by_link(self, obj):
        """Display approver as link"""
        if obj.approved_by:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:accounts_user_change', args=[obj.approved_by.pk]),
                obj.approved_by.get_full_name() or obj.approved_by.email
            )
        return '-'
    approved_by_link.short_description = 'Approved By'
    
    def created_at_formatted(self, obj):
        """Format creation date"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'
    
    def approved_at_formatted(self, obj):
        """Format approval date"""
        if obj.approved_at:
            return obj.approved_at.strftime('%Y-%m-%d %H:%M')
        return '-'
    approved_at_formatted.short_description = 'Approved'
    approved_at_formatted.admin_order_field = 'approved_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('approved_by').prefetch_related('items')


@admin.register(MarketProcurementItem)
class MarketProcurementItemAdmin(admin.ModelAdmin):
    list_display = (
        'product_link', 'recommendation_link', 'priority_colored',
        'quantity_info', 'cost_info', 'supplier_link',
        'procurement_method_colored'
    )
    list_filter = (
        'priority', 'procurement_method', 'is_fambri_available',
        'recommendation__status', 'product__department',
        'preferred_supplier',
    )
    search_fields = (
        'product__name', 'reasoning', 'product__department__name',
        'preferred_supplier__name'
    )
    readonly_fields = ('estimated_total_cost',)
    
    fieldsets = (
        ('Item Information', {
            'fields': ('recommendation', 'product', 'priority')
        }),
        ('Quantities', {
            'fields': ('needed_quantity', 'recommended_quantity')
        }),
        ('Pricing', {
            'fields': ('estimated_unit_price', 'estimated_total_cost', 'supplier_unit_price')
        }),
        ('Supplier Information', {
            'fields': (
                'preferred_supplier', 'supplier_product', 'supplier_quality_rating',
                'supplier_lead_time_days', 'is_fambri_available'
            ),
            'classes': ('collapse',)
        }),
        ('Procurement Strategy', {
            'fields': ('procurement_method', 'reasoning')
        }),
        ('Source Data', {
            'fields': ('source_orders',),
            'classes': ('collapse',)
        }),
    )
    
    def product_link(self, obj):
        """Display product as link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:products_product_change', args=[obj.product.pk]),
            obj.product.name
        )
    product_link.short_description = 'Product'
    product_link.admin_order_field = 'product__name'
    
    def recommendation_link(self, obj):
        """Display recommendation date as link"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:products_marketprocurementrecommendation_change', args=[obj.recommendation.pk]),
            obj.recommendation.for_date.strftime('%Y-%m-%d')
        )
    recommendation_link.short_description = 'Recommendation Date'
    recommendation_link.admin_order_field = 'recommendation__for_date'
    
    def priority_colored(self, obj):
        """Display priority with color coding"""
        colors = {
            'critical': '#dc3545',  # Red
            'high': '#fd7e14',      # Orange
            'medium': '#ffc107',    # Yellow
            'low': '#28a745',       # Green
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_colored.short_description = 'Priority'
    priority_colored.admin_order_field = 'priority'
    
    def quantity_info(self, obj):
        """Display quantity information"""
        return f'{obj.recommended_quantity} (need: {obj.needed_quantity})'
    quantity_info.short_description = 'Quantity (Recommended/Needed)'
    quantity_info.admin_order_field = 'recommended_quantity'
    
    def cost_info(self, obj):
        """Display cost information"""
        return f'R{obj.estimated_total_cost:,.2f} (@R{obj.estimated_unit_price})'
    cost_info.short_description = 'Total Cost (@Unit Price)'
    cost_info.admin_order_field = 'estimated_total_cost'
    
    def supplier_link(self, obj):
        """Display supplier as link"""
        if obj.preferred_supplier:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:suppliers_supplier_change', args=[obj.preferred_supplier.pk]),
                obj.preferred_supplier.name
            )
        return format_html('<em>No supplier</em>')
    supplier_link.short_description = 'Supplier'
    supplier_link.admin_order_field = 'preferred_supplier__name'
    
    def procurement_method_colored(self, obj):
        """Display procurement method with color coding"""
        colors = {
            'market': '#007bff',     # Blue
            'supplier': '#28a745',   # Green
            'fambri': '#6f42c1',     # Purple
            'mixed': '#fd7e14',      # Orange
        }
        color = colors.get(obj.procurement_method, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_procurement_method_display()
        )
    procurement_method_colored.short_description = 'Method'
    procurement_method_colored.admin_order_field = 'procurement_method'