from django.contrib import admin
from .models import Invoice, InvoiceItem, Payment, CreditNote

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ['line_total']

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

class CreditNoteInline(admin.TabularInline):
    model = CreditNote
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'status', 'invoice_date', 'due_date', 'total_amount', 'balance_due', 'is_overdue']
    list_filter = ['status', 'invoice_date', 'due_date', 'created_at']
    search_fields = ['invoice_number', 'customer__email', 'customer__first_name', 'customer__last_name']
    readonly_fields = ['invoice_number', 'tax_amount', 'total_amount', 'balance_due', 'is_overdue', 'days_overdue', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline, PaymentInline, CreditNoteInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('invoice_number', 'order', 'customer', 'status')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date', 'paid_date')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_rate', 'tax_amount', 'discount_amount', 'total_amount', 'amount_paid', 'balance_due')
        }),
        ('Status Information', {
            'fields': ('is_overdue', 'days_overdue')
        }),
        ('Additional Information', {
            'fields': ('notes', 'payment_terms')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product_name', 'quantity', 'unit_price', 'line_total']
    list_filter = ['invoice__status', 'created_at']
    search_fields = ['invoice__invoice_number', 'product_name', 'description']
    readonly_fields = ['line_total']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'payment_date', 'reference_number', 'processed_by']
    list_filter = ['payment_method', 'payment_date', 'processed_by']
    search_fields = ['invoice__invoice_number', 'reference_number', 'bank_reference']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('invoice', 'amount', 'payment_method', 'payment_date')
        }),
        ('Reference Details', {
            'fields': ('reference_number', 'bank_reference')
        }),
        ('Processing', {
            'fields': ('processed_by', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = ['credit_note_number', 'invoice', 'amount', 'reason', 'credit_date', 'approved_by']
    list_filter = ['reason', 'credit_date', 'approved_by']
    search_fields = ['credit_note_number', 'invoice__invoice_number', 'description']
    readonly_fields = ['credit_note_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('credit_note_number', 'invoice', 'amount', 'reason')
        }),
        ('Details', {
            'fields': ('description', 'credit_date', 'approved_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )