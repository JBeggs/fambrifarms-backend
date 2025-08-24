from django.contrib import admin
from .models import ProductionReservation


@admin.register(ProductionReservation)
class ProductionReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "quantity_reserved", "uom", "status", "scheduled_for", "created_at")
    list_filter = ("status", "scheduled_for", "product")
    search_fields = ("id", "order_item__id", "product__name")


