from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import WhatsAppMessage, SalesRep, PurchaseOrder, POItem
from .serializers import (
    WhatsAppMessageSerializer, 
    SalesRepSerializer, 
    PurchaseOrderSerializer
)
from orders.models import Order, OrderItem
from products.models import Product
import json

# WhatsApp Message Views
class WhatsAppMessageListView(generics.ListCreateAPIView):
    queryset = WhatsAppMessage.objects.all()
    serializer_class = WhatsAppMessageSerializer
    permission_classes = [IsAuthenticated]

class WhatsAppMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = WhatsAppMessage.objects.all()
    serializer_class = WhatsAppMessageSerializer
    permission_classes = [IsAuthenticated]

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_whatsapp_message(request):
    """Receive a WhatsApp message for processing"""
    data = request.data
    
    # Create WhatsApp message record
    message = WhatsAppMessage.objects.create(
        message_id=data.get('message_id', f"manual_{timezone.now().timestamp()}"),
        sender_phone=data.get('sender_phone', ''),
        sender_name=data.get('sender_name', ''),
        message_text=data.get('message_text', ''),
    )
    
    return Response({
        'message_id': message.id,
        'status': 'received',
        'message': 'WhatsApp message received successfully'
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_whatsapp_message(request, message_id):
    """Parse WhatsApp message using AI/manual patterns"""
    try:
        message = WhatsAppMessage.objects.get(id=message_id)
    except WhatsAppMessage.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Simple pattern matching for now (will add AI later)
    parsed_items = parse_message_simple(message.message_text)
    
    # Update message with parsing results
    message.parsed_items = parsed_items
    message.parsing_confidence = calculate_confidence(parsed_items)
    message.parsing_method = 'manual_patterns'
    message.save()
    
    return Response({
        'message_id': message.id,
        'parsed_items': parsed_items,
        'confidence': message.parsing_confidence,
        'needs_review': message.parsing_confidence < 0.7
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_parsing(request, message_id):
    """Manager confirms/corrects parsing result and creates order"""
    try:
        message = WhatsAppMessage.objects.get(id=message_id)
    except WhatsAppMessage.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    
    confirmed_items = request.data.get('items', [])
    order_date = request.data.get('order_date')
    
    # Validate order date
    if not order_date:
        return Response({'error': 'Order date is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from datetime import datetime
        order_date = datetime.strptime(order_date, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create order
    order = Order.objects.create(
        restaurant=request.user,  # For now, use current user
        order_date=order_date,
        whatsapp_message_id=message.message_id,
        original_message=message.message_text,
        parsed_by_ai=True,
        status='confirmed'
    )
    
    # Create order items
    for item_data in confirmed_items:
        try:
            product = Product.objects.get(name=item_data['product_name'])
        except Product.DoesNotExist:
            # Create a simple product record for now
            product = Product.objects.create(
                name=item_data['product_name'],
                price=item_data.get('price', 50),  # Default price
                unit=item_data.get('unit', 'kg')
            )
        
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item_data['quantity'],
            unit=item_data.get('unit', 'kg'),
            price=product.price,
            original_text=item_data.get('original_text', ''),
            confidence_score=item_data.get('confidence', 0),
            manually_corrected=item_data.get('manually_corrected', False)
        )
    
    # Mark message as processed
    message.processed = True
    message.order = order
    message.processed_at = timezone.now()
    message.save()
    
    return Response({
        'order_id': order.id,
        'order_number': order.order_number,
        'status': 'confirmed',
        'delivery_date': order.delivery_date.isoformat()
    })

# Sales Rep Views
class SalesRepListView(generics.ListCreateAPIView):
    queryset = SalesRep.objects.filter(is_active=True)
    serializer_class = SalesRepSerializer
    permission_classes = [IsAuthenticated]

class SalesRepDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SalesRep.objects.all()
    serializer_class = SalesRepSerializer
    permission_classes = [IsAuthenticated]

# Purchase Order Views
class PurchaseOrderListView(generics.ListCreateAPIView):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

class PurchaseOrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_purchase_order(request):
    """Generate purchase order from confirmed order"""
    order_id = request.data.get('order_id')
    sales_rep_id = request.data.get('sales_rep_id')
    
    try:
        order = Order.objects.get(id=order_id)
        sales_rep = SalesRep.objects.get(id=sales_rep_id)
    except (Order.DoesNotExist, SalesRep.DoesNotExist):
        return Response({'error': 'Order or Sales Rep not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Create purchase order
    po = PurchaseOrder.objects.create(
        order=order,
        sales_rep=sales_rep,
        delivery_date=order.delivery_date,
        status='draft'
    )
    
    # Create PO items
    for order_item in order.items.all():
        POItem.objects.create(
            purchase_order=po,
            product_name=order_item.product.name,
            quantity_requested=order_item.quantity,
            unit=order_item.unit
        )
    
    return Response({
        'po_id': po.id,
        'po_number': po.po_number,
        'sales_rep': sales_rep.name,
        'status': 'created'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_po_to_sales_rep(request, po_id):
    """Generate WhatsApp message for PO (manual copy/paste for now)"""
    try:
        po = PurchaseOrder.objects.get(id=po_id)
    except PurchaseOrder.DoesNotExist:
        return Response({'error': 'Purchase Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Generate WhatsApp message
    message = generate_po_whatsapp_message(po)
    
    # Update PO status
    po.status = 'sent'
    po.whatsapp_message_sent = message
    po.sent_at = timezone.now()
    po.save()
    
    return Response({
        'po_number': po.po_number,
        'whatsapp_message': message,
        'sales_rep_number': po.sales_rep.whatsapp_number,
        'status': 'ready_to_send'
    })

# Helper functions
def parse_message_simple(message_text):
    """Simple pattern matching for common orders"""
    import re
    
    patterns = {
        r'(\d+)\s*x?\s*onions?': {'product': 'Red Onions', 'unit': 'kg', 'default_qty': 5},
        r'(\d+)\s*x?\s*tomatoes?': {'product': 'Tomatoes', 'unit': 'kg', 'default_qty': 3},
        r'(\d+)\s*x?\s*potatoes?': {'product': 'Potatoes', 'unit': 'kg', 'default_qty': 10},
        r'(\d+)\s*kg\s*(\w+)': {'extract_product': True, 'unit': 'kg'},
    }
    
    items = []
    message_lower = message_text.lower()
    
    for pattern, config in patterns.items():
        matches = re.finditer(pattern, message_lower)
        for match in matches:
            if config.get('extract_product'):
                # Pattern like "5 kg potatoes"
                quantity = int(match.group(1))
                product_name = match.group(2).title()
            else:
                # Pattern like "2 x onions"
                quantity = int(match.group(1)) if match.group(1) else config.get('default_qty', 1)
                product_name = config['product']
            
            items.append({
                'product_name': product_name,
                'quantity': quantity,
                'unit': config['unit'],
                'confidence': 0.8,
                'original_text': match.group(0)
            })
    
    return items

def calculate_confidence(parsed_items):
    """Calculate overall confidence score"""
    if not parsed_items:
        return 0.0
    
    total_confidence = sum(item.get('confidence', 0) for item in parsed_items)
    return total_confidence / len(parsed_items)

def generate_po_whatsapp_message(po):
    """Generate formatted WhatsApp message for PO"""
    message = f"""🛒 *PURCHASE ORDER #{po.po_number}*
📅 Date: {po.created_at.strftime('%Y-%m-%d')}
🏪 Customer: {po.order.restaurant.first_name} {po.order.restaurant.last_name}
⏰ Needed by: {po.delivery_date.strftime('%A, %B %d')}

📦 *ITEMS NEEDED:*
"""
    
    for item in po.items.all():
        message += f"• {item.product_name}: {item.quantity_requested}{item.unit}\n"
    
    message += f"""
💰 Budget: R{po.estimated_total or 'TBD'}
🎯 Quality: Fresh, Grade A
📍 Delivery: Fambri Farms

*PLEASE CONFIRM:*
✅ Availability
💰 Final pricing  
⏰ Pickup time
📦 Quality grade

*Reply format:*
CONFIRM {po.po_number} - [your response]

*Deadline: {(po.created_at + timezone.timedelta(hours=2)).strftime('%H:%M today')}*
Thanks! 🙏"""
    
    return message