from django.contrib import admin
from .models import Supplier, SupplierProduct

class SupplierProductInline(admin.TabularInline):
    model = SupplierProduct
    extra = 0
    readonly_fields = ('id',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    inlines = (SupplierProductInline,)
    
    list_display = ('name', 'contact_name', 'contact_email', 'city', 'is_active')
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'contact_name', 'contact_email')
    
    fieldsets = (
        (None, {'fields': ('name', 'is_active')}),
        ('Contact Information', {'fields': ('contact_name', 'contact_email', 'contact_phone')}),
        ('Address', {'fields': ('address', 'city', 'postal_code')}),
    )

@admin.register(SupplierProduct)
class SupplierProductAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'product', 'supplier_price', 'stock_quantity', 'is_available')
    list_filter = ('is_available', 'supplier', 'product__department')
    search_fields = ('supplier__name', 'product__name')
    list_editable = ('supplier_price', 'stock_quantity', 'is_available') 