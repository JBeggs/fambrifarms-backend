from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import SupplierPurchaseOrder, SupplierPOItem
from .serializers import SupplierPOSerializer
from orders.models import Order, OrderItem

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def generate_pos_from_order(request):
    order_id = request.data.get('order_id')
    order = get_object_or_404(Order, id=order_id)

    # Group order items by supplier
    supplier_to_items = {}
    for item in order.items.all():
        if item.fulfillment_source == 'internal':
            continue
        supplier = item.supplier
        if not supplier:
            # Skip items without supplier for now (could auto-assign later)
            continue
        supplier_to_items.setdefault(supplier.id, []).append(item)

    created_pos = []
    for supplier_id, items in supplier_to_items.items():
        po = SupplierPurchaseOrder.objects.create(
            supplier_id=supplier_id,
            created_by=request.user,
            order=order,
            status='draft'
        )
        for it in items:
            SupplierPOItem.objects.create(
                po=po,
                order_item=it,
                product=it.product,
                quantity=it.quantity,
                price=it.supplier_price or it.price,
            )
        created_pos.append(po)

    data = SupplierPOSerializer(created_pos, many=True).data
    return Response({'purchase_orders': data}, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def purchase_order_detail(request, po_id):
    po = get_object_or_404(SupplierPurchaseOrder, id=po_id)

    if request.method == 'GET':
        return Response(SupplierPOSerializer(po).data)

    # PATCH: update status/expected_date/notes
    status_val = request.data.get('status')
    expected_date = request.data.get('expected_date')
    notes = request.data.get('notes')

    if status_val:
        po.status = status_val
    if expected_date:
        po.expected_date = expected_date
    if notes is not None:
        po.notes = notes
    po.save()

    return Response(SupplierPOSerializer(po).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def receive_purchase_order(request, po_id):
    po = get_object_or_404(SupplierPurchaseOrder, id=po_id)
    items_payload = request.data.get('items', [])

    # items: [{po_item_id, received_quantity}]
    for item_data in items_payload:
        po_item = get_object_or_404(SupplierPOItem, id=item_data.get('po_item_id'), po=po)
        recv_qty = item_data.get('received_quantity', 0)
        po_item.received_quantity = (po_item.received_quantity or 0) + recv_qty
        po_item.save()

    # Update PO status
    if all(i.received_quantity >= i.quantity for i in po.items.all()):
        po.status = 'received'
    elif any(i.received_quantity > 0 for i in po.items.all()):
        po.status = 'partial'
    po.save()

    return Response(SupplierPOSerializer(po).data)
