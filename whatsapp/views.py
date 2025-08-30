"""
WhatsApp Integration Views
Handles WhatsApp message processing, parsing, and order creation
"""
import logging
from decimal import Decimal
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import WhatsAppMessage, SalesRep, PurchaseOrder, POItem
from .serializers import WhatsAppMessageSerializer, SalesRepSerializer, PurchaseOrderSerializer
from .utils import parse_whatsapp_message
from orders.models import Order, OrderItem
from products.models import Product

User = get_user_model()
logger = logging.getLogger(__name__)


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
def receive_message(request):
    """
    Receive and store WhatsApp message for processing
    
    Expected payload:
    {
        "sender_phone": "+27123456789",
        "sender_name": "Restaurant ABC", 
        "message_text": "Hi, can I get 2 x onions and 3kg tomatoes?",
        "message_id": "whatsapp_msg_123" (optional)
    }
    """
    try:
        sender_phone = request.data.get('sender_phone')
        sender_name = request.data.get('sender_name')
        message_text = request.data.get('message_text')
        message_id = request.data.get('message_id', f"manual_{timezone.now().strftime('%Y%m%d_%H%M%S')}")
        
        if not all([sender_phone, sender_name, message_text]):
            return Response({
                "error": "Missing required fields: sender_phone, sender_name, message_text"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if message already exists
        if WhatsAppMessage.objects.filter(message_id=message_id).exists():
            return Response({
                "error": "Message already exists",
                "message_id": message_id
            }, status=status.HTTP_409_CONFLICT)
        
        # Create WhatsApp message record
        whatsapp_message = WhatsAppMessage.objects.create(
            message_id=message_id,
            sender_phone=sender_phone,
            sender_name=sender_name,
            message_text=message_text,
            processed=False
        )
        
        # Auto-parse the message
        parsing_result = parse_whatsapp_message(message_text, use_claude=False)
        
        # Store parsing results
        whatsapp_message.parsed_items = parsing_result.get('items', [])
        whatsapp_message.parsing_confidence = parsing_result.get('confidence', 0.0)
        whatsapp_message.save()
        
        logger.info(f"Received WhatsApp message from {sender_name}: {len(parsing_result.get('items', []))} items parsed")
        
        return Response({
            "message_id": whatsapp_message.id,
            "whatsapp_message_id": message_id,
            "parsing_result": parsing_result,
            "status": "received_and_parsed",
            "needs_review": parsing_result.get('needs_review', True)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error receiving WhatsApp message: {e}")
        return Response({
            "error": "Failed to process WhatsApp message",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unparsed_messages(request):
    """Get all unparsed WhatsApp messages for manager review"""
    
    unparsed_messages = WhatsAppMessage.objects.filter(
        processed=False
    ).order_by('-created_at')
    
    serializer = WhatsAppMessageSerializer(unparsed_messages, many=True)
    
    return Response({
        "unparsed_messages": serializer.data,
        "count": unparsed_messages.count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_message(request, message_id):
    """
    Re-parse WhatsApp message using AI/pattern matching
    
    Optional payload:
    {
        "use_claude": true  // Force Claude API usage
    }
    """
    try:
        whatsapp_message = get_object_or_404(WhatsAppMessage, id=message_id)
        
        if whatsapp_message.processed:
            return Response({
                "error": "Message already processed",
                "order_id": whatsapp_message.order.id if whatsapp_message.order else None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        use_claude = request.data.get('use_claude', False)
        
        # Re-parse the message
        parsing_result = parse_whatsapp_message(whatsapp_message.message_text, use_claude=use_claude)
        
        # Update stored parsing results
        whatsapp_message.parsed_items = parsing_result.get('items', [])
        whatsapp_message.parsing_confidence = parsing_result.get('confidence', 0.0)
        whatsapp_message.save()
        
        logger.info(f"Re-parsed message {message_id} with method: {parsing_result.get('parsing_method')}")
        
        return Response({
            "message_id": message_id,
            "parsing_result": parsing_result,
            "updated": True
        })
        
    except Exception as e:
        logger.error(f"Error parsing message {message_id}: {e}")
        return Response({
            "error": "Failed to parse message",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_parsing(request, message_id):
    """
    Manager confirms/corrects AI parsing results and creates order
    
    Expected payload:
    {
        "confirmed_items": [
            {
                "product_name": "Red Onions",
                "quantity": 5.0,
                "unit": "kg",
                "manually_corrected": false,
                "original_text": "2 x onions"
            }
        ],
        "restaurant_name": "Restaurant ABC" (optional, uses sender_name if not provided)
    }
    """
    try:
        whatsapp_message = get_object_or_404(WhatsAppMessage, id=message_id)
        
        if whatsapp_message.processed:
            return Response({
                "error": "Message already processed",
                "order_id": whatsapp_message.order.id if whatsapp_message.order else None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        confirmed_items = request.data.get('confirmed_items', [])
        restaurant_name = request.data.get('restaurant_name', whatsapp_message.sender_name)
        
        if not confirmed_items:
            return Response({
                "error": "No confirmed items provided"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Get or create restaurant user (simplified for now)
            restaurant_user, created = User.objects.get_or_create(
                username=f"restaurant_{whatsapp_message.sender_phone}",
                defaults={
                    'email': f"{whatsapp_message.sender_phone}@restaurant.com",
                    'first_name': restaurant_name,
                    'is_active': True
                }
            )
            
            # Create order
            order = Order.objects.create(
                restaurant=restaurant_user,
                whatsapp_message_id=whatsapp_message.message_id,
                original_message=whatsapp_message.message_text,
                parsed_by_ai=True,
                status='confirmed'
            )
            
            # Create order items
            total_items_created = 0
            for item_data in confirmed_items:
                try:
                    # Get or create product
                    product, created = Product.objects.get_or_create(
                        name=item_data['product_name'],
                        defaults={
                            'description': f'Product from WhatsApp order',
                            'unit': item_data.get('unit', 'kg'),
                            'is_active': True
                        }
                    )
                    
                    # Create order item
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=Decimal(str(item_data['quantity'])),
                        unit=item_data.get('unit', 'kg'),
                        original_text=item_data.get('original_text', ''),
                        confidence_score=item_data.get('confidence', 0.0),
                        manually_corrected=item_data.get('manually_corrected', False)
                    )
                    
                    total_items_created += 1
                    
                except Exception as item_error:
                    logger.error(f"Error creating order item {item_data}: {item_error}")
                    continue
            
            # Mark message as processed
            whatsapp_message.processed = True
            whatsapp_message.order = order
            whatsapp_message.save()
            
            logger.info(f"Created order {order.order_number} from WhatsApp message {message_id} with {total_items_created} items")
            
            return Response({
                "order_id": order.id,
                "order_number": order.order_number,
                "status": "confirmed",
                "items_created": total_items_created,
                "restaurant": restaurant_name,
                "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"Error confirming parsing for message {message_id}: {e}")
        return Response({
            "error": "Failed to create order from parsed message",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
def generate_po(request, order_id):
    """
    Generate Purchase Order for sales rep
    
    Creates PO and formats WhatsApp message for sales rep
    """
    try:
        order = get_object_or_404(Order, id=order_id)
        
        if order.status not in ['confirmed']:
            return Response({
                "error": f"Order must be confirmed to generate PO. Current status: {order.status}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if PO already exists
        if hasattr(order, 'purchase_order'):
            return Response({
                "error": "Purchase Order already exists for this order",
                "po_id": order.purchase_order.id,
                "po_number": order.purchase_order.po_number
            }, status=status.HTTP_409_CONFLICT)
        
        # Get an active sales rep (simplified - could be more sophisticated)
        sales_rep = SalesRep.objects.filter(is_active=True).first()
        if not sales_rep:
            return Response({
                "error": "No active sales rep available"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create Purchase Order
            po = PurchaseOrder.objects.create(
                manager=request.user,
                sales_rep=sales_rep,
                order=order,
                status='draft'
            )
            
            # Create PO items from order items
            total_amount = Decimal('0.00')
            for order_item in order.items.all():
                # Use product price or default price
                unit_price = getattr(order_item.product, 'price', Decimal('10.00'))  # Default price
                line_total = unit_price * order_item.quantity
                
                POItem.objects.create(
                    purchase_order=po,
                    product=order_item.product,
                    quantity=order_item.quantity,
                    unit=order_item.unit,
                    price=unit_price,
                    total_price=line_total
                )
                
                total_amount += line_total
            
            # Update PO total
            po.total_amount = total_amount
            po.save()
            
            # Update order status
            order.status = 'po_sent'
            order.save()
            
            logger.info(f"Generated PO {po.po_number} for order {order.order_number}")
            
            return Response({
                "po_id": po.id,
                "po_number": po.po_number,
                "sales_rep": sales_rep.name,
                "total_amount": float(total_amount),
                "items_count": po.items.count(),
                "status": "draft"
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"Error generating PO for order {order_id}: {e}")
        return Response({
            "error": "Failed to generate Purchase Order",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_po_whatsapp_message(request, po_id):
    """
    Get formatted WhatsApp message for sending PO to sales rep
    
    Returns formatted message for copy/paste to WhatsApp
    """
    try:
        po = get_object_or_404(PurchaseOrder, id=po_id)
        
        # Format WhatsApp message
        message_lines = [
            f"🛒 *Purchase Order: {po.po_number}*",
            f"📅 Delivery: {po.order.delivery_date.strftime('%A, %d %B %Y')}",
            f"🏪 Restaurant: {po.order.restaurant.first_name}",
            "",
            "*Items needed:*"
        ]
        
        for item in po.items.all():
            message_lines.append(f"• {item.product.name}: {item.quantity}{item.unit} @ R{item.price}")
        
        message_lines.extend([
            "",
            f"💰 *Total: R{po.total_amount}*",
            "",
            "Please confirm availability and pricing.",
            f"Reply with: CONFIRM {po.po_number}"
        ])
        
        whatsapp_message = "\n".join(message_lines)
        
        return Response({
            "po_id": po_id,
            "po_number": po.po_number,
            "sales_rep_name": po.sales_rep.name,
            "sales_rep_phone": po.sales_rep.whatsapp_number,
            "whatsapp_message": whatsapp_message,
            "instructions": f"Copy this message and send to {po.sales_rep.name} on WhatsApp ({po.sales_rep.whatsapp_number})"
        })
        
    except Exception as e:
        logger.error(f"Error generating WhatsApp message for PO {po_id}: {e}")
        return Response({
            "error": "Failed to generate WhatsApp message",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_po(request, po_id):
    """
    Mark PO as sent to sales rep
    
    Expected payload:
    {
        "sent_via": "whatsapp",  // or "email", "sms"
        "notes": "Sent to John at 14:30"
    }
    """
    try:
        po = get_object_or_404(PurchaseOrder, id=po_id)
        
        if po.status != 'draft':
            return Response({
                "error": f"PO must be in draft status to send. Current status: {po.status}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark as sent
        po.status = 'sent'
        po.sent_at = timezone.now()
        po.save()
        
        # Update order status
        po.order.status = 'po_sent'
        po.order.save()
        
        logger.info(f"Marked PO {po.po_number} as sent to {po.sales_rep.name}")
        
        return Response({
            "po_id": po_id,
            "po_number": po.po_number,
            "status": "sent",
            "sent_at": po.sent_at.isoformat(),
            "sales_rep": po.sales_rep.name
        })
        
    except Exception as e:
        logger.error(f"Error marking PO {po_id} as sent: {e}")
        return Response({
            "error": "Failed to mark PO as sent",
            "details": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Backward compatibility aliases
receive_whatsapp_message = receive_message
parse_whatsapp_message = parse_message
generate_purchase_order = generate_po
send_po_to_sales_rep = send_po