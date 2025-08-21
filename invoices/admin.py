from django.contrib import admin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'restaurant', 'status', 'total_amount', 'issue_date', 'due_date')
    list_filter = ('status', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'restaurant__email', 'restaurant__restaurantprofile__business_name')
    readonly_fields = ('invoice_number', 'created_at', 'tax_amount', 'total_amount')
    
    fieldsets = (
        (None, {'fields': ('restaurant', 'order', 'invoice_number', 'status')}),
        ('Dates', {'fields': ('issue_date', 'due_date')}),
        ('Financial', {'fields': ('subtotal', 'tax_amount', 'total_amount')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('restaurant', 'order')
        return self.readonly_fields 