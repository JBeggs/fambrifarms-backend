from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from .models import Order, OrderItem
from .serializers import OrderSerializer
from products.models import Product
import re

User = get_user_model()

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.user_type == 'admin':
            return Order.objects.all().order_by('-created_at')
        return Order.objects.filter(restaurant=self.request.user).order_by('-created_at')

class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.user_type == 'admin':
            return Order.objects.all()
        return Order.objects.filter(restaurant=self.request.user)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """Admin endpoint to update order status"""
    if request.user.user_type != 'admin':
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    order = get_object_or_404(Order, id=order_id)
    new_status = request.data.get('status')
    
    if new_status not in ['pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled']:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    order.status = new_status
    order.save()
    
    serializer = OrderSerializer(order)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])  # Light security for now
def create_order_from_whatsapp(request):
    """
    Endpoint for social-hub to create orders from WhatsApp messages
    """
    try:
        data = request.data
        
        # Extract WhatsApp message data
        whatsapp_message_id = data.get('whatsapp_message_id')
        sender = data.get('sender')
        sender_name = data.get('sender_name')
        message_text = data.get('message_text')
        timestamp = data.get('timestamp')
        is_backdated = data.get('is_backdated', False)
        customer_id = data.get('customer_id')  # For manual order creation
        
        if not all([whatsapp_message_id, message_text]):
            return Response({
                'error': 'Missing required fields: whatsapp_message_id, message_text'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find restaurant user - either by customer_id or sender
        if customer_id:
            try:
                restaurant_user = User.objects.get(id=customer_id, user_type='restaurant')
            except User.DoesNotExist:
                return Response({
                    'error': f'Customer with ID {customer_id} not found'
                }, status=status.HTTP_400_BAD_REQUEST)
        elif sender:
            restaurant_user = get_or_create_restaurant_user(sender, sender_name)
        else:
            return Response({
                'error': 'Either customer_id or sender must be provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate next valid order date (Monday or Thursday)
        order_date = get_next_order_date()
        
        # Create order
        order = Order.objects.create(
            restaurant=restaurant_user,
            order_date=order_date,
            status='received' if not customer_id else 'manual_entry',  # Different status for manual orders
            whatsapp_message_id=whatsapp_message_id,
            original_message=message_text,
            parsed_by_ai=False if not customer_id else True  # Manual orders are considered "parsed"
        )
        
        # Handle items differently for manual vs automated orders
        parsed_items = []
        items_data = data.get('items', [])  # Expect pre-parsed items from frontend
        
        if items_data and customer_id:  # Manual order with pre-parsed items
            for item_data in items_data:
                product_name = item_data.get('name', '').strip()
                quantity = item_data.get('quantity', 1)
                unit = item_data.get('unit', '').strip()
                original_text = item_data.get('originalText', '')
                
                if product_name:
                    # Find matching product
                    product = find_product_by_name(product_name)
                    
                    if product:
                        parsed_items.append({
                            'product': product,
                            'quantity': quantity,
                            'unit': unit,
                            'original_text': original_text,
                            'confidence': 1.0  # Manual selection = high confidence
                        })
        else:
            # Automated parsing for legacy WhatsApp messages
            parsed_items = parse_order_message(message_text)
        
        # Create order items
        for item_data in parsed_items:
            product = item_data.get('product')
            quantity = item_data.get('quantity', 1)
            confidence = item_data.get('confidence', 0.5)
            
            if product:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=product.price,
                    original_text=item_data.get('original_text', ''),
                    confidence_score=confidence,
                    manually_corrected=customer_id is not None  # Mark as manually corrected if from frontend
                )
        
        # Update order status based on parsing success
        if parsed_items:
            order.status = 'parsed' if not customer_id else 'confirmed'  # Manual orders go straight to confirmed
            if not customer_id:
                order.parsed_by_ai = True
        else:
            order.status = 'needs_review'
        
        order.save()
        
        return Response({
            'success': True,
            'order_id': order.id,
            'status': order.status,
            'items_parsed': len(parsed_items),
            'message': f'Order created successfully from WhatsApp message'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to create order: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_or_create_restaurant_user(sender, sender_name):
    """
    Find or create a restaurant user based on WhatsApp sender
    """
    # Clean phone number
    phone = re.sub(r'[^\d+]', '', sender)
    
    # Try to find existing user by phone or email
    user = None
    try:
        # Look for user with phone in email (temporary approach)
        user = User.objects.get(email__contains=phone.replace('+', ''))
    except User.DoesNotExist:
        # Create new restaurant user
        email = f"whatsapp_{phone.replace('+', '')}@fambrifarms.temp"
        user = User.objects.create_user(
            email=email,
            first_name=sender_name or 'WhatsApp',
            last_name='Restaurant',
            user_type='restaurant',
            phone=phone
        )
    
    return user

def get_next_order_date():
    """
    Calculate next valid order date (Monday=0 or Thursday=3)
    """
    from django.utils import timezone
    
    today = timezone.now().date()
    current_weekday = today.weekday()
    
    # If today is Monday (0) or Thursday (3), use today
    if current_weekday in [0, 3]:
        return today
    
    # Otherwise find next Monday or Thursday
    if current_weekday < 3:  # Before Thursday
        days_until_thursday = 3 - current_weekday
        return today + timedelta(days=days_until_thursday)
    else:  # After Thursday
        days_until_monday = 7 - current_weekday
        return today + timedelta(days=days_until_monday)

def parse_order_message(message_text):
    """
    Basic parsing of WhatsApp order messages
    Returns list of parsed items with products and quantities
    """
    parsed_items = []
    
    # Common patterns for orders
    patterns = [
        r'(\d+)\s*(?:kg|kgs?)\s+(\w+)',  # "5kg onions"
        r'(\d+)\s*(?:x|X)\s+(\w+)',      # "5x onions" 
        r'(\d+)\s+(\w+)',                # "5 onions"
        r'(\w+)\s*[:-]\s*(\d+)',         # "onions: 5"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, message_text, re.IGNORECASE)
        for match in matches:
            try:
                if pattern.startswith(r'(\w+)'):  # Product first
                    product_name = match.group(1)
                    quantity = int(match.group(2))
                else:  # Quantity first
                    quantity = int(match.group(1))
                    product_name = match.group(2)
                
                # Find matching product
                product = find_product_by_name(product_name)
                
                if product:
                    parsed_items.append({
                        'product': product,
                        'quantity': quantity,
                        'original_text': match.group(0),
                        'confidence': 0.8  # High confidence for pattern match
                    })
            except (ValueError, IndexError):
                continue
    
    return parsed_items

def find_product_by_name(product_name):
    """
    Find product by name or common names
    """
    try:
        # Direct name match
        return Product.objects.get(name__icontains=product_name)
    except Product.DoesNotExist:
        pass
    
    # Try common names (if available)
    try:
        products = Product.objects.filter(common_names__icontains=product_name)
        if products.exists():
            return products.first()
    except:
        pass
    
    # Fuzzy matching for common vegetables
    name_mappings = {
        'onion': 'onions',
        'potato': 'potatoes', 
        'tomato': 'tomatoes',
        'carrot': 'carrots',
        'cabbage': 'cabbage',
        'lettuce': 'lettuce',
        'spinach': 'spinach',
        'pepper': 'peppers'
    }
    
    for key, value in name_mappings.items():
        if key in product_name.lower():
            try:
                return Product.objects.get(name__icontains=value)
            except Product.DoesNotExist:
                continue
    
    return None 