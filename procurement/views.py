from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.utils import timezone
from .models import PurchaseOrder, PurchaseOrderItem
from suppliers.models import Supplier, SalesRep
from products.models import Product
from rest_framework import serializers

class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'

@api_view(['POST'])
@permission_classes([AllowAny])
def create_simple_purchase_order(request):
    """
    Create a purchase order with proper supplier and sales rep
    """
    try:
        data = request.data
        
        # Check if this is a production order
        is_production = data.get('is_production')
        if is_production is None:
            is_production = False  # Explicit default for order type
        
        # Get the supplier (not required for production orders)
        supplier = None
        supplier_id = data.get('supplier_id')
        
        if is_production:
            # For production orders, supplier is optional
            if supplier_id:
                try:
                    supplier = Supplier.objects.get(id=supplier_id)
                except Supplier.DoesNotExist:
                    return Response(
                        {'error': 'Supplier not found'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
        else:
            # For purchase orders, supplier is required
            if not supplier_id:
                return Response(
                    {'error': 'Supplier ID is required for purchase orders'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                supplier = Supplier.objects.get(id=supplier_id)
            except Supplier.DoesNotExist:
                return Response(
                    {'error': 'Supplier not found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get the sales rep if provided
        sales_rep = None
        sales_rep_id = data.get('sales_rep_id')
        if sales_rep_id:
            try:
                sales_rep = SalesRep.objects.get(id=sales_rep_id, supplier=supplier)
            except SalesRep.DoesNotExist:
                return Response(
                    {'error': 'Sales rep not found for this supplier'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get the product
        try:
            product = Product.objects.get(id=data.get('product_id'))
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create purchase order
        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                supplier=supplier,
                sales_rep=sales_rep,
                status='draft',
                order_date=timezone.now().date(),
                expected_delivery_date=data.get('expected_delivery_date'),
                notes=data.get('notes') or ''
            )
            
            # Create purchase order item
            quantity_raw = data.get('quantity')
            quantity = int(quantity_raw) if quantity_raw is not None else 1
            unit_price_raw = data.get('unit_price')
            unit_price = float(unit_price_raw) if unit_price_raw is not None else 0.0
            
            po_item = PurchaseOrderItem.objects.create(
                purchase_order=po,
                product=product,
                quantity_ordered=quantity,
                unit_price=unit_price,
                total_price=quantity * unit_price
            )
            
            # Update PO totals
            po.subtotal = po_item.total_price
            po.total_amount = po_item.total_price
            po.save()
        
        return Response({
            'success': True,
            'purchase_order_id': po.id,
            'po_number': po.po_number,
            'message': f'Purchase order {po.po_number} created successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to create purchase order: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
