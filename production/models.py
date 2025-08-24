import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class ProductionBatch(models.Model):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    batch_number = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="production_batches",
    )
    
    planned_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    actual_quantity = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        null=True, 
        blank=True
    )
    uom = models.CharField(max_length=32, default="unit")
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PLANNED
    )
    
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_end_date = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_production_batches",
    )

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["planned_start_date"]),
            models.Index(fields=["product"]),
            models.Index(fields=["batch_number"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(planned_quantity__gt=0),
                name="productionbatch_planned_quantity_gt_zero",
            ),
        ]
        ordering = ["-created_at"]

    def start_production(self):
        """Mark the batch as started"""
        if not self.actual_start_date:
            self.actual_start_date = timezone.now()
            self.status = self.Status.IN_PROGRESS
            self.save(update_fields=["actual_start_date", "status", "updated_at"])

    def complete_production(self, actual_quantity=None):
        """Mark the batch as completed"""
        if not self.actual_end_date:
            self.actual_end_date = timezone.now()
            self.status = self.Status.COMPLETED
            if actual_quantity is not None:
                self.actual_quantity = actual_quantity
            self.save(update_fields=["actual_end_date", "status", "actual_quantity", "updated_at"])

    def __str__(self) -> str:
        return f"Batch {self.batch_number} - {self.product} ({self.status})"


class ProductionReservation(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SCHEDULED = "SCHEDULED", "Scheduled"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.PROTECT,
        related_name="production_reservations",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="production_reservations",
    )

    quantity_reserved = models.DecimalField(max_digits=12, decimal_places=3)
    uom = models.CharField(max_length=32, default="unit")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_for = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    batch = models.ForeignKey(
        "production.ProductionBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )

    notes = models.TextField(blank=True, default="")
    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_production_reservations",
    )

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["scheduled_for"]),
            models.Index(fields=["product"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity_reserved__gt=0),
                name="productionreservation_quantity_gt_zero",
            ),
        ]
        ordering = ["-created_at"]

    def mark_started(self):
        if not self.started_at:
            self.started_at = timezone.now()
            self.status = self.Status.IN_PROGRESS
            self.save(update_fields=["started_at", "status", "updated_at"])

    def mark_completed(self):
        if not self.completed_at:
            self.completed_at = timezone.now()
            self.status = self.Status.COMPLETED
            self.save(update_fields=["completed_at", "status", "updated_at"])

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity_reserved} for {self.order_item_id} ({self.status})"


