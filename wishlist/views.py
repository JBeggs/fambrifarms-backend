from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
from .models import Wishlist, WishlistItem
from products.models import Product
from orders.models import Order, OrderItem
from .serializers import WishlistSerializer, WishlistItemSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wishlist(request):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    serializer = WishlistSerializer(wishlist)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_wishlists(request):
    """Admin endpoint to get all wishlists"""
    if request.user.user_type != 'admin':
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    wishlists = Wishlist.objects.all().select_related('user').prefetch_related('items__product')
    serializer = WishlistSerializer(wishlists, many=True)
    return Response({
        'count': wishlists.count(),
        'next': None,
        'previous': None,
        'results': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_wishlist(request):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)
    notes = request.data.get('notes', '')
    
    product = get_object_or_404(Product, id=product_id)
    
    wishlist_item, created = WishlistItem.objects.get_or_create(
        wishlist=wishlist,
        product=product,
        defaults={'quantity': quantity, 'notes': notes}
    )
    
    if not created:
        wishlist_item.quantity = quantity
        wishlist_item.notes = notes
        wishlist_item.save()
    
    serializer = WishlistItemSerializer(wishlist_item)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_to_order(request):
    wishlist = get_object_or_404(Wishlist, user=request.user)
    
    if not wishlist.items.exists():
        return Response({'error': 'Wishlist is empty'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if today is an order day (Tuesday = 1, Friday = 4)
    today = timezone.now().weekday()
    if today not in [1, 4]:  # Tuesday and Friday
        return Response({
            'error': 'Orders can only be placed on Tuesdays and Fridays'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Calculate total
    total_amount = sum(item.product.price * item.quantity for item in wishlist.items.all())
    
    # Create order
    order = Order.objects.create(
        restaurant=request.user,  # Changed from user to restaurant
        total_amount=total_amount,
        subtotal=total_amount,
        status='pending'
    )
    
    # Create order items
    for item in wishlist.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price,
            total_price=item.product.price * item.quantity
        )
    
    # Clear wishlist
    wishlist.items.all().delete()
    
    return Response({
        'order_number': order.order_number,
        'message': 'Order created successfully'
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_order_day(request):
    """Check if today is an order day"""
    today = timezone.now().weekday()
    is_order_day = today in [1, 4]  # Tuesday and Friday
    
    return Response({
        'is_order_day': is_order_day,
        'message': 'Today is an order day' if is_order_day else 'Orders can only be placed on Tuesdays and Fridays'
    }) 