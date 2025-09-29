from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import PurchaseOrder, PurchaseOrderItem
from suppliers.models import Supplier, SalesRep
from products.models import Product
from orders.models import Order
from rest_framework import serializers
from .services import FambriFirstProcurementService
from products.unified_procurement_service import UnifiedProcurementService

class PurchaseOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = '__all__'

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'

class CreatePurchaseOrderSerializer(serializers.Serializer):
    """Serializer for creating purchase orders with validation"""
    is_production = serializers.BooleanField(default=False)
    supplier_id = serializers.IntegerField(required=False, allow_null=True)
    sales_rep_id = serializers.IntegerField(required=False, allow_null=True)
    items = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        error_messages={'min_length': 'At least one item is required'}
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    
    def validate(self, data):
        is_production = data.get('is_production', False)
        supplier_id = data.get('supplier_id')
        
        # For purchase orders (not production), supplier is required
        if not is_production and not supplier_id:
            raise serializers.ValidationError({
                'supplier_id': 'Supplier ID is required for purchase orders'
            })
        
        # Validate items structure
        items = data.get('items', [])
        for i, item in enumerate(items):
            if 'product_id' not in item:
                raise serializers.ValidationError({
                    'items': f'Item {i+1}: product_id is required'
                })
            if 'quantity' not in item:
                raise serializers.ValidationError({
                    'items': f'Item {i+1}: quantity is required'
                })
            try:
                quantity = float(item['quantity'])
                if quantity <= 0:
                    raise serializers.ValidationError({
                        'items': f'Item {i+1}: quantity must be greater than 0'
                    })
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    'items': f'Item {i+1}: quantity must be a valid number'
                })
        
        return data

@api_view(['POST'])
@permission_classes([AllowAny])
def create_simple_purchase_order(request):
    """
    Create a purchase order with proper supplier and sales rep
    """
    # Validate input data using serializer
    serializer = CreatePurchaseOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                'error': 'Invalid input data',
                'message': 'Please check your input and try again',
                'details': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        data = serializer.validated_data
        is_production = data['is_production']
        supplier_id = data.get('supplier_id')
        
        # Get the supplier if provided
        supplier = None
        if supplier_id:
            try:
                supplier = Supplier.objects.get(id=supplier_id)
            except Supplier.DoesNotExist:
                return Response(
                    {
                        'error': 'Supplier not found',
                        'message': f'Supplier with ID {supplier_id} does not exist'
                    }, 
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
        
        # Get the order if provided (for linking PO to customer order)
        order = None
        order_id = data.get('order_id')
        if order_id:
            try:
                from orders.models import Order
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                pass  # Continue without linking to order
        
        # Create purchase order
        with transaction.atomic():
            po = PurchaseOrder.objects.create(
                supplier=supplier,
                sales_rep=sales_rep,
                order=order,  # Link to customer order if provided
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

# Fambri-First Procurement Workflow Endpoints
@api_view(['POST'])
@permission_classes([AllowAny])
def analyze_order_procurement(request):
    """
    Analyze an order for procurement using Fambri-first logic
    POST data: {'order_id': int}
    """
    try:
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({
                'error': 'order_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order = get_object_or_404(Order, id=order_id)
        
        # Initialize unified procurement service
        procurement_service = UnifiedProcurementService()
        
        # Analyze order procurement using unified logic
        result = procurement_service.create_procurement_from_order(order)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to analyze order procurement: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def process_order_workflow(request):
    """
    Process complete procurement workflow for an order
    POST data: {'order_id': int, 'auto_create_pos': bool}
    """
    try:
        order_id = request.data.get('order_id')
        auto_create_pos = request.data.get('auto_create_pos', False)
        
        if not order_id:
            return Response({
                'error': 'order_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order = get_object_or_404(Order, id=order_id)
        
        # Initialize procurement service
        procurement_service = FambriFirstProcurementService()
        
        # Process complete workflow
        result = procurement_service.process_order_procurement_workflow(
            order, auto_create_pos=auto_create_pos
        )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to process order workflow: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_low_stock_recommendations(request):
    """
    Get procurement recommendations for products with low stock
    """
    try:
        # Initialize procurement service
        procurement_service = FambriFirstProcurementService()
        
        # Get low stock recommendations
        result = procurement_service.get_procurement_recommendations_for_low_stock()
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to get low stock recommendations: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
