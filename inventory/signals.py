"""
Django signals for automatic stock management integration
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from .models import (
    StockMovement, FinishedInventory, RawMaterialBatch, 
    StockAlert, ProductionBatch
)

User = get_user_model()


@receiver(post_save, sender='orders.Order')
def handle_order_status_change(sender, instance, created, **kwargs):
    """
    Handle stock movements when order status changes
    """
    # Get the order instance
    order = instance
    
    # Handle different status changes (both on creation and updates)
    if order.status == 'confirmed':
        # Reserve stock for confirmed orders
        # Check if stock is already reserved to avoid double reservation
        existing_reservations = StockMovement.objects.filter(
            movement_type='finished_reserve',
            reference_number=order.order_number
        ).exists()
        
        if not existing_reservations:
            reserve_stock_for_order(order)
    
    elif order.status == 'delivered':
        # Mark stock as sold
        # Check if stock is already sold to avoid double processing
        existing_sales = StockMovement.objects.filter(
            movement_type='finished_sell',
            reference_number=order.order_number
        ).exists()
        
        if not existing_sales:
            sell_stock_for_order(order)
            # Check for production alerts after delivery
            check_production_alerts_for_order(order)
    
    elif order.status == 'cancelled':
        # Release reserved stock
        # Only release if there are reservations to release
        existing_reservations = StockMovement.objects.filter(
            movement_type='finished_reserve',
            reference_number=order.order_number
        ).exists()
        
        if existing_reservations:
            release_stock_for_order(order)


def reserve_stock_for_order(order):
    """
    Reserve stock when order is confirmed
    """
    for item in order.items.all():
        try:
            inventory = FinishedInventory.objects.get(product=item.product)
            
            if inventory.reserve_stock(item.quantity):
                # Create stock movement record
                StockMovement.objects.create(
                    movement_type='finished_reserve',
                    reference_number=order.order_number,
                    product=item.product,
                    quantity=item.quantity,
                    unit_cost=item.price,
                    total_value=item.total_price,
                    user=order.restaurant,  # Customer who placed the order
                    notes=f"Reserved for order {order.order_number}"
                )
            else:
                # Create alert for insufficient stock
                StockAlert.objects.create(
                    alert_type='out_of_stock',
                    product=item.product,
                    message=f"Insufficient stock for order {order.order_number}. Required: {item.quantity}, Available: {inventory.available_quantity}",
                    severity='critical'
                )
                
        except FinishedInventory.DoesNotExist:
            # Create alert for missing inventory record
            StockAlert.objects.create(
                alert_type='out_of_stock',
                product=item.product,
                message=f"No inventory record exists for {item.product.name}",
                severity='critical'
            )


def sell_stock_for_order(order):
    """
    Mark reserved stock as sold when order is delivered
    """
    for item in order.items.all():
        try:
            inventory = FinishedInventory.objects.get(product=item.product)
            
            if inventory.sell_stock(item.quantity):
                # Create stock movement record
                StockMovement.objects.create(
                    movement_type='finished_sell',
                    reference_number=order.order_number,
                    product=item.product,
                    quantity=item.quantity,
                    unit_cost=item.price,
                    total_value=item.total_price,
                    user=order.restaurant,
                    notes=f"Sold via order {order.order_number}"
                )
                
                # Check if production is needed
                if inventory.needs_production:
                    StockAlert.objects.create(
                        alert_type='production_needed',
                        product=item.product,
                        message=f"{item.product.name} inventory below reorder level ({inventory.available_quantity} remaining, reorder at {inventory.reorder_level})",
                        severity='medium'
                    )
                    
        except FinishedInventory.DoesNotExist:
            pass  # Already handled in reserve_stock


def release_stock_for_order(order):
    """
    Release reserved stock when order is cancelled
    """
    for item in order.items.all():
        try:
            inventory = FinishedInventory.objects.get(product=item.product)
            inventory.release_stock(item.quantity)
            
            # Create stock movement record
            StockMovement.objects.create(
                movement_type='finished_release',
                reference_number=order.order_number,
                product=item.product,
                quantity=item.quantity,
                unit_cost=item.price,
                total_value=item.total_price,
                user=order.restaurant,
                notes=f"Released due to order cancellation {order.order_number}"
            )
            
        except FinishedInventory.DoesNotExist:
            pass


# @receiver(post_save, sender='suppliers.PurchaseOrderItem')
# def handle_purchase_receipt(sender, instance, created, **kwargs):
#     """
#     Handle stock increases when purchase order items are received
#     """
#     if not created and instance.quantity_received > 0:
#         po_item = instance
#         
#         if po_item.product:
#             # Finished product received directly from supplier
#             handle_finished_product_receipt(po_item)
#         
#         elif po_item.raw_material:
#             # Raw material received - create batch
#             handle_raw_material_receipt(po_item)


# def handle_finished_product_receipt(po_item):
#     """
#     Handle receipt of finished products directly from supplier
#     """
#     # Get or create finished inventory
#     inventory, created = FinishedInventory.objects.get_or_create(
#         product=po_item.product,
#         defaults={
#             'available_quantity': Decimal('0'),
#             'reserved_quantity': Decimal('0'),
#             'minimum_level': Decimal('10'),  # Default minimum
#             'reorder_level': Decimal('20'),  # Default reorder level
#             'average_cost': po_item.unit_price
#         }
#     )
#     
#     # Update inventory quantities
#     inventory.available_quantity += po_item.quantity_received
#     
#     # Update average cost using weighted average
#     total_value = (inventory.total_quantity * inventory.average_cost) + (po_item.quantity_received * po_item.unit_price)
#     total_quantity = inventory.total_quantity + po_item.quantity_received
#     
#     if total_quantity > 0:
#         inventory.average_cost = total_value / total_quantity
#     
#     inventory.save()
#     
#     # Create stock movement record
#     StockMovement.objects.create(
#         movement_type='finished_adjust',
#         reference_number=po_item.purchase_order.po_number,
#         product=po_item.product,
#         quantity=po_item.quantity_received,
#         unit_cost=po_item.unit_price,
#         total_value=po_item.quantity_received * po_item.unit_price,
#         user_id=po_item.purchase_order.ordered_by_id,
#         notes=f"Received from supplier {po_item.purchase_order.supplier.name}"
#     )


# def handle_raw_material_receipt(po_item):
#     """
#     Handle receipt of raw materials - create batch tracking
#     """
#     from .models import RawMaterialBatch
#     
#     # Create batch for raw material
#     batch = RawMaterialBatch.objects.create(
#         raw_material=po_item.raw_material,
#         supplier=po_item.purchase_order.supplier,
#         received_quantity=po_item.quantity_received,
#         available_quantity=po_item.quantity_received,
#         unit_cost=po_item.unit_price,
#         received_date=timezone.now(),
#         notes=f"Received via PO {po_item.purchase_order.po_number}"
#     )
#     
#     # Calculate expiry date if shelf life is known
#     if po_item.raw_material.shelf_life_days:
#         from datetime import timedelta
#         batch.expiry_date = batch.received_date.date() + timedelta(days=po_item.raw_material.shelf_life_days)
#         batch.save()
#     
#     # Create stock movement record
#     StockMovement.objects.create(
#         movement_type='raw_receive',
#         reference_number=po_item.purchase_order.po_number,
#         raw_material=po_item.raw_material,
#         raw_material_batch=batch,
#         quantity=po_item.quantity_received,
#         unit_cost=po_item.unit_price,
#         total_value=po_item.quantity_received * po_item.unit_price,
#         user_id=po_item.purchase_order.ordered_by_id,
#         notes=f"Batch {batch.batch_number} received from {po_item.purchase_order.supplier.name}"
#     )


@receiver(post_save, sender=ProductionBatch)
def handle_production_completion(sender, instance, created, **kwargs):
    """
    Handle stock movements when production is completed
    """
    if instance.status == 'completed' and instance.actual_quantity:
        production_batch = instance
        
        # Create/update finished inventory
        inventory, created = FinishedInventory.objects.get_or_create(
            product=production_batch.recipe.product,
            defaults={
                'available_quantity': Decimal('0'),
                'reserved_quantity': Decimal('0'),
                'minimum_level': Decimal('10'),
                'reorder_level': Decimal('20'),
                'average_cost': production_batch.cost_per_unit
            }
        )
        
        # Update inventory
        inventory.available_quantity += production_batch.actual_quantity
        
        # Update average cost
        total_value = (inventory.total_quantity * inventory.average_cost) + (production_batch.actual_quantity * production_batch.cost_per_unit)
        total_quantity = inventory.total_quantity + production_batch.actual_quantity
        
        if total_quantity > 0:
            inventory.average_cost = total_value / total_quantity
        
        inventory.save()
        
        # Create stock movement for production output
        StockMovement.objects.create(
            movement_type='production',
            reference_number=production_batch.batch_number,
            product=production_batch.recipe.product,
            quantity=production_batch.actual_quantity,
            unit_cost=production_batch.cost_per_unit,
            total_value=production_batch.actual_quantity * production_batch.cost_per_unit,
            user=production_batch.produced_by or production_batch.planned_by,
            notes=f"Production batch {production_batch.batch_number} completed"
        )
        
        # Handle waste if any
        if production_batch.waste_quantity > 0:
            StockMovement.objects.create(
                movement_type='production_waste',
                reference_number=production_batch.batch_number,
                product=production_batch.recipe.product,
                quantity=production_batch.waste_quantity,
                unit_cost=production_batch.cost_per_unit,
                total_value=production_batch.waste_quantity * production_batch.cost_per_unit,
                user=production_batch.produced_by or production_batch.planned_by,
                notes=f"Production waste from batch {production_batch.batch_number}"
            )


@receiver(pre_save, sender=RawMaterialBatch)
def check_expiring_raw_materials(sender, instance, **kwargs):
    """
    Create alerts for raw materials approaching expiry
    """
    if instance.expiry_date:
        days_until_expiry = instance.days_until_expiry
        
        if days_until_expiry is not None:
            if days_until_expiry <= 0:
                # Already expired
                StockAlert.objects.get_or_create(
                    alert_type='expired',
                    raw_material_batch=instance,
                    defaults={
                        'message': f"Raw material batch {instance.batch_number} has expired",
                        'severity': 'critical'
                    }
                )
            elif days_until_expiry <= 3:
                # Expiring soon
                StockAlert.objects.get_or_create(
                    alert_type='expiring_soon',
                    raw_material_batch=instance,
                    defaults={
                        'message': f"Raw material batch {instance.batch_number} expires in {days_until_expiry} days",
                        'severity': 'high'
                    }
                )


@receiver(post_save, sender='products.Product')
def ensure_finished_inventory_exists(sender, instance, created, **kwargs):
    """
    Ensure FinishedInventory record exists for every product
    """
    if created:
        FinishedInventory.objects.get_or_create(
            product=instance,
            defaults={
                'available_quantity': Decimal('0'),
                'reserved_quantity': Decimal('0'),
                'minimum_level': Decimal('10'),
                'reorder_level': Decimal('20'),
                'average_cost': instance.price  # Use product price as initial cost
            }
        )


@receiver(post_save, sender=FinishedInventory)
def update_stock_alerts(sender, instance, **kwargs):
    """
    Update stock alerts when FinishedInventory changes
    """
    from inventory.models import StockAlert
    
    # Clear existing alerts for this product
    StockAlert.objects.filter(
        product=instance.product,
        alert_type__in=['low_stock', 'out_of_stock']
    ).delete()
    
    # Create new alert if needed
    if instance.available_quantity <= 0:
        StockAlert.objects.create(
            alert_type='out_of_stock',
            product=instance.product,
            message=f'{instance.product.name} is OUT OF STOCK! Available: {instance.available_quantity} {instance.product.unit}',
            severity='critical'
        )
    elif instance.available_quantity <= instance.minimum_level:
        severity = 'high' if instance.available_quantity <= (instance.minimum_level * Decimal('0.5')) else 'medium'
        StockAlert.objects.create(
            alert_type='low_stock',
            product=instance.product,
            message=f'{instance.product.name} is running low. Available: {instance.available_quantity} {instance.product.unit}, Minimum: {instance.minimum_level} {instance.product.unit}',
            severity=severity
        )


def check_production_alerts_for_order(order):
    """Check if production alerts should be created after order delivery"""
    from .models import FinishedInventory, StockAlert
    
    for item in order.items.all():
        try:
            inventory = FinishedInventory.objects.get(product=item.product)
            
            # Check if stock is below reorder level
            if inventory.available_quantity <= inventory.reorder_level:
                # Check if alert already exists
                existing_alert = StockAlert.objects.filter(
                    alert_type='production_needed',
                    product=item.product,
                    is_active=True
                ).exists()
                
                if not existing_alert:
                    StockAlert.objects.create(
                        alert_type='production_needed',
                        product=item.product,
                        severity='medium',
                        message=f'Production needed for {item.product.name}. Current stock: {inventory.available_quantity}, Reorder level: {inventory.reorder_level}',
                        is_active=True
                    )
                    
        except FinishedInventory.DoesNotExist:
            pass  # No inventory found
        except Exception as e:
            pass  # Handle silently in production
