from django.contrib import admin
from .models import ProductionBatch, ProductionReservation


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "product", "planned_quantity", "actual_quantity", "uom", "status", "planned_start_date", "created_at")
    list_filter = ("status", "planned_start_date", "product")
    search_fields = ("batch_number", "product__name", "notes")
    readonly_fields = ("actual_start_date", "actual_end_date")
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("batch_number", "product", "status", "notes")
        }),
        ("Planning", {
            "fields": ("planned_quantity", "uom", "planned_start_date", "planned_end_date", "created_by")
        }),
        ("Execution", {
            "fields": ("actual_quantity", "actual_start_date", "actual_end_date")
        }),
    )


@admin.register(ProductionReservation)
class ProductionReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "quantity_reserved", "uom", "status", "scheduled_for", "created_at")
    list_filter = ("status", "scheduled_for", "product")
    search_fields = ("id", "order_item__id", "product__name")


