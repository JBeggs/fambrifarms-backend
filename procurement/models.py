from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class SupplierPurchaseOrder(models.Model):
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.CASCADE, related_name='purchase_orders')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='supplier_pos')
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('confirmed', 'Confirmed'),
        ('received', 'Received'),
        ('partial', 'Partial'),
        ('cancelled', 'Cancelled'),
    ], default='draft')
    expected_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PO {self.id} - {self.supplier.name} - {self.status}"

class SupplierPOItem(models.Model):
    po = models.ForeignKey(SupplierPurchaseOrder, on_delete=models.CASCADE, related_name='items')
    order_item = models.OneToOneField('orders.OrderItem', on_delete=models.CASCADE, related_name='po_item')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"PO#{self.po_id} - {self.product.name} ({self.quantity})"
