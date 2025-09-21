from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import datetime, timedelta
from .models import Order, OrderItem
from .serializers import OrderSerializer
from products.models import Product
import re

User = get_user_model()

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]  # Temporarily allow access for development
    
    def get_queryset(self):
        # For development - return all orders since we don't have auth
        return Order.objects.select_related(
            'restaurant', 
            'restaurant__restaurantprofile'
        ).prefetch_related(
            'items__product__department'
        ).order_by('-created_at')

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]  # Temporarily allow access for development
    
    def get_queryset(self):
        # For development - return all orders since we don't have auth
        return Order.objects.select_related(
            'restaurant', 
            'restaurant__restaurantprofile'
        ).prefetch_related(
            'items__product__department'
        )

class CustomerOrdersView(generics.ListAPIView):
    """Get orders for a specific customer"""
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]  # Temporarily allow access for development
    
    def get_queryset(self):
        customer_id = self.kwargs.get('customer_id')
        if customer_id:
            return Order.objects.filter(
                restaurant_id=customer_id
            ).select_related(
                'restaurant', 
                'restaurant__restaurantprofile'
            ).prefetch_related(
                'items__product__department'
            ).order_by('-created_at')
        return Order.objects.none()
    
    def update(self, request, *args, **kwargs):
        """Handle order updates including items"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle order items if provided
        items_data = request.data.get('items', [])
        
        # Update basic order fields
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Save the order first
        order = serializer.save()
        
        # Handle items update if provided
        if items_data:
            # Clear existing items
            order.items.all().delete()
            
            # Create new items
            for item_data in items_data:
                product_id = item_data.get('product')
                
                # Validate required fields
                if not product_id:
                    return Response(
                        {'error': 'product field is required for each item'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                quantity = item_data.get('quantity')
                if quantity is None:
                    return Response(
                        {'error': 'quantity field is required for each item'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    quantity = float(quantity)
                    if quantity <= 0:
                        return Response(
                            {'error': 'quantity must be greater than 0'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        {'error': 'quantity must be a valid number'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                price = item_data.get('price', 0)  # Price can default to 0, will be calculated if needed
                
                if product_id:
                    try:
                        product = Product.objects.get(id=product_id)
                        # Use provided price if specified, otherwise get customer-specific price
                        if price <= 0:
                            price = product.get_customer_price(order.restaurant)
                        
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price=price,
                            unit=item_data.get('unit', ''),
                            original_text=item_data.get('original_text', ''),
                            manually_corrected=True  # Mark as manually edited
                        )
                    except Product.DoesNotExist:
                        continue
        
        # Recalculate totals
        order.subtotal = sum(item.total_price for item in order.items.all())
        order.total_amount = order.subtotal
        order.save()
        
        # Return updated order
        return Response(OrderSerializer(order).data)
    
    def destroy(self, request, *args, **kwargs):
        """Handle order deletion"""
        instance = self.get_object()
        order_number = instance.order_number
        
        # Log the deletion for audit purposes
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Deleting order {order_number} (ID: {instance.id})")
        
        # Perform the deletion
        self.perform_destroy(instance)
        
        return Response(
            {"message": f"Order {order_number} deleted successfully"}, 
            status=status.HTTP_200_OK
        )

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
        is_backdated = data.get('is_backdated')
        if is_backdated is None:
            is_backdated = False  # Explicit default for order dating
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
        items_data = data.get('items')
        if items_data is None:
            items_data = []  # Explicit default for items list
        
        if items_data and customer_id:  # Manual order with pre-parsed items
            for item_data in items_data:
                product_name = (item_data.get('name') or '').strip()
                quantity = item_data.get('quantity')
                if quantity is None:
                    quantity = 1
                unit = (item_data.get('unit') or '').strip()
                original_text = item_data.get('originalText') or ''
                
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
            quantity = item_data.get('quantity')
            if quantity is None:
                quantity = 1
            confidence = item_data.get('confidence')
            if confidence is None:
                confidence = 0.5
            
            if product:
                # Get customer-specific price from active price list
                customer_price = product.get_customer_price(restaurant_user)
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=customer_price,
                    original_text=item_data.get('original_text') or '',
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
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Order creation failed: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return Response({
            'error': 'Unable to create order',
            'message': 'An error occurred while processing your order. Please check your order details and try again.',
            'details': str(e) if settings.DEBUG else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_or_create_restaurant_user(sender, sender_name):
    """
    Find or create a restaurant user based on WhatsApp sender
    """
    # Clean phone number
    phone = re.sub(r'[^\d+]', '', sender)
    
    # Try to find existing user by phone or email
    # Look for user with phone in email (temporary approach)
    user = User.objects.filter(email__contains=phone.replace('+', '')).first()
    
    if not user:
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
    Find product by name or common names with precise matching
    """
    if not product_name:
        return None
    
    product_name = product_name.strip()
    
    # 1. Try exact name match first (case insensitive)
    product = Product.objects.filter(name__iexact=product_name).first()
    if product:
        return product
    
    # 2. Try exact match in common_names
    try:
        products = Product.objects.filter(common_names__icontains=f'"{product_name}"')  # Look for quoted exact match
        if products.exists():
            return products.first()
    except Exception:
        pass
    
    # Try common names (if available)
    try:
        products = Product.objects.filter(common_names__icontains=product_name)
        if products.exists():
            return products.first()
    except Exception as e:
        # Log the error but continue with other matching strategies
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error searching common names for '{product_name}': {e}")
        # Continue to next matching strategy
    
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
            # Use filter().first() to avoid MultipleObjectsReturned error
            product = Product.objects.filter(name__icontains=value).first()
            if product:
                return product
    
    return None 