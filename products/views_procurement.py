"""
Procurement Intelligence API Views for Fambri Farms
Handles market recommendations, buffer management, and recipe operations
"""

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction, models
from datetime import datetime, timedelta
import logging

from .models import (
    Product, ProcurementBuffer, MarketProcurementRecommendation, 
    MarketProcurementItem, Recipe
)
from .services import ProcurementIntelligenceService, RecipeService
from .serializers import ProductSerializer
from rest_framework import serializers

logger = logging.getLogger(__name__)

# Serializers
class ProcurementBufferSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcurementBuffer
        fields = '__all__'

class MarketProcurementItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_department = serializers.CharField(source='product.department.name', read_only=True)
    
    class Meta:
        model = MarketProcurementItem
        fields = '__all__'

class MarketProcurementRecommendationSerializer(serializers.ModelSerializer):
    items = MarketProcurementItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)
    
    class Meta:
        model = MarketProcurementRecommendation
        fields = '__all__'

class RecipeSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = Recipe
        fields = '__all__'

# API Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_market_recommendation(request):
    """
    Generate intelligent market procurement recommendation
    
    POST /api/products/procurement/generate-recommendation/
    Body: {
        "for_date": "2025-01-20" (optional, defaults to today or earliest order date),
        "use_historical_dates": true (optional, defaults to true for backdating)
    }
    """
    try:
        # Parse request data
        for_date_str = request.data.get('for_date')
        use_historical_dates = request.data.get('use_historical_dates', True)
        
        if for_date_str:
            for_date = datetime.strptime(for_date_str, '%Y-%m-%d').date()
        else:
            for_date = None  # Let service determine the date
        
        # Generate recommendation
        service = ProcurementIntelligenceService()
        
        # FORCE UPDATE: Clear all existing buffers to use current business settings
        from .models import ProcurementBuffer
        from .models_business_settings import BusinessSettings
        from decimal import Decimal
        
        # Get current business settings
        business_settings = BusinessSettings.get_settings()
        print(f"🔧 Using business settings: {business_settings.default_spoilage_rate*100:.1f}% + {business_settings.default_cutting_waste_rate*100:.1f}% + {business_settings.default_quality_rejection_rate*100:.1f}% = {(business_settings.default_spoilage_rate + business_settings.default_cutting_waste_rate + business_settings.default_quality_rejection_rate)*100:.1f}% total")
        
        # Update ALL existing buffers to current business settings BEFORE generating
        buffers = ProcurementBuffer.objects.all()
        updated_count = 0
        for buffer in buffers:
            # Calculate new total from business settings
            total_buffer = float(business_settings.default_spoilage_rate + business_settings.default_cutting_waste_rate + business_settings.default_quality_rejection_rate)
            
            # Force update to current settings
            buffer.spoilage_rate = business_settings.default_spoilage_rate
            buffer.cutting_waste_rate = business_settings.default_cutting_waste_rate  
            buffer.quality_rejection_rate = business_settings.default_quality_rejection_rate
            buffer.total_buffer_rate = Decimal(str(total_buffer))
            buffer.market_pack_size = business_settings.default_market_pack_size  # FIX: Update pack size too!
            buffer.save()
            updated_count += 1
            
        print(f"🔄 Force-updated {updated_count} buffers to current business settings")
        
        recommendation = service.generate_market_recommendation(for_date, use_historical_dates)
        
        # Serialize response
        serializer = MarketProcurementRecommendationSerializer(recommendation)
        
        return Response({
            'success': True,
            'message': f'Generated market recommendation for {for_date}',
            'recommendation': serializer.data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error generating market recommendation: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_market_recommendations(request):
    """
    Get list of market procurement recommendations
    
    GET /api/products/procurement/recommendations/
    Query params:
    - status: filter by status (pending, approved, purchased, cancelled)
    - days_back: how many days back to look (default: 30)
    """
    try:
        # Parse query parameters
        status_filter = request.GET.get('status')
        days_back = int(request.GET.get('days_back', 30))
        
        # Build query
        queryset = MarketProcurementRecommendation.objects.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = timezone.now().date() - timedelta(days=days_back)
        queryset = queryset.filter(for_date__gte=start_date)
        
        # Order by most recent first
        queryset = queryset.order_by('-created_at')
        
        # Serialize
        serializer = MarketProcurementRecommendationSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'recommendations': serializer.data,
            'count': queryset.count()
        })
        
    except Exception as e:
        logger.error(f"Error fetching market recommendations: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_market_recommendation(request, recommendation_id):
    """
    Approve a market procurement recommendation and complete order workflow
    
    This endpoint:
    1. Approves the procurement recommendation
    2. Confirms ALL unconfirmed orders (pending/received → confirmed status)
    3. Soft-deletes ALL processed WhatsApp messages (marks is_deleted=True)
    4. Resets all stock levels to 0 (prevents carryover to next procurement cycle)
    
    POST /api/products/procurement/recommendations/{id}/approve/
    Body: {
        "notes": "Optional approval notes"
    }
    
    When approved, this completes the current order cycle and prepares the system
    for the next stock take and procurement cycle by clearing all processed data.
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        
        if recommendation.status != 'pending':
            return Response({
                'success': False,
                'error': f'Cannot approve recommendation with status: {recommendation.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Step 1: Update recommendation
        recommendation.status = 'approved'
        recommendation.approved_by = request.user
        recommendation.approved_at = timezone.now()
        recommendation.notes = request.data.get('notes', '')
        recommendation.save()
        
        # Step 2: Confirm all unconfirmed orders (handles both 'pending' and 'received' statuses)
        # The procurement recommendation covers all current unconfirmed orders
        orders_confirmed_count = 0
        try:
            from orders.models import Order
            
            # First, check how many orders exist and their status
            total_orders = Order.objects.count()
            pending_orders = Order.objects.filter(status='pending').count()
            received_orders = Order.objects.filter(status='received').count()
            confirmed_orders = Order.objects.filter(status='confirmed').count()
            
            logger.info(f"Order stats: {total_orders} total, {pending_orders} pending, {received_orders} received, {confirmed_orders} confirmed")
            
            # Look for orders that need confirmation (both 'pending' and 'received')
            unconfirmed_orders = Order.objects.filter(status__in=['pending', 'received'])
            
            logger.info(f"Found {unconfirmed_orders.count()} unconfirmed orders to confirm")
            
            for order in unconfirmed_orders:
                old_status = order.status
                order.status = 'confirmed'
                order.save()
                orders_confirmed_count += 1
                logger.debug(f"Confirmed order {order.id} ({old_status} → confirmed)")
                
            logger.info(f"Confirmed {orders_confirmed_count} unconfirmed orders (pending/received)")
        except Exception as e:
            logger.error(f"Error confirming orders: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't fail approval if order confirmation fails
        
        # Step 3: Soft-delete ALL non-deleted WhatsApp messages (complete cycle cleanup)
        # This clears all messages to prepare for the next order cycle
        messages_deleted_count = 0
        try:
            from whatsapp.models import WhatsAppMessage
            
            # First, check how many messages exist and their status
            total_messages = WhatsAppMessage.objects.count()
            already_deleted = WhatsAppMessage.objects.filter(is_deleted=True).count()
            not_deleted = WhatsAppMessage.objects.filter(is_deleted=False).count()
            
            logger.info(f"Message stats: {total_messages} total, {already_deleted} already deleted, {not_deleted} not deleted")
            
            # Get ALL messages that aren't already soft-deleted
            messages = WhatsAppMessage.objects.filter(is_deleted=False)
            
            logger.info(f"Found {messages.count()} messages to soft-delete (ALL non-deleted)")
            
            for message in messages:
                message.is_deleted = True
                message.save()
                messages_deleted_count += 1
                logger.debug(f"Soft-deleted message {message.id} from {message.sender_name}")
                
            logger.info(f"Soft-deleted {messages_deleted_count} WhatsApp messages (ALL non-deleted)")
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Don't fail approval if message deletion fails
        
        # Step 4: Reset all stock levels to 0 (prepare for next stock take)
        # This prevents stock carryover between procurement cycles
        stock_reset_count = 0
        try:
            from whatsapp.services import reset_all_stock_levels
            reset_summary = reset_all_stock_levels()
            stock_reset_count = reset_summary.get('total_reset', 0)
            logger.info(f"Reset {stock_reset_count} stock items to 0 for next cycle")
        except Exception as e:
            logger.warning(f"Error resetting stock levels: {e}")
            # Don't fail approval if stock reset fails
        
        # Serialize response
        serializer = MarketProcurementRecommendationSerializer(recommendation)
        
        return Response({
            'success': True,
            'message': f'Market recommendation approved. {orders_confirmed_count} orders confirmed. {messages_deleted_count} messages deleted. {stock_reset_count} stock items reset.',
            'recommendation': serializer.data,
            'print_url': f'/api/products/procurement/recommendations/{recommendation_id}/print/',
            'orders_confirmed': orders_confirmed_count,
            'messages_deleted': messages_deleted_count,
            'stock_reset': stock_reset_count
        })
        
    except MarketProcurementRecommendation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recommendation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error approving recommendation: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_market_recommendation(request, recommendation_id):
    """
    Update a market recommendation and its items
    
    PUT /api/products/procurement/recommendations/{id}/
    Body: {
        "for_date": "2025-09-04",
        "items": [
            {
                "id": 1,  // Optional - if provided, updates existing item
                "product_id": 5,
                "needed_quantity": 10.0,
                "recommended_quantity": 12.0,
                "estimated_unit_price": 15.75,
                "priority": "high"
            }
        ]
    }
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        
        if recommendation.status == 'approved':
            return Response({
                'success': False,
                'error': 'Cannot edit approved recommendations'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Update recommendation metadata
            if 'for_date' in request.data:
                recommendation.for_date = request.data['for_date']
            
            # Update items if provided
            if 'items' in request.data:
                items_data = request.data['items']
                total_cost = 0
                
                # Track existing item IDs to know which ones to keep
                updated_item_ids = []
                
                for item_data in items_data:
                    item_id = item_data.get('id')
                    
                    if item_id:
                        # Update existing item
                        try:
                            item = MarketProcurementItem.objects.get(
                                id=item_id, 
                                recommendation=recommendation
                            )
                            item.needed_quantity = item_data.get('needed_quantity', item.needed_quantity)
                            item.recommended_quantity = item_data.get('recommended_quantity', item.recommended_quantity)
                            item.estimated_unit_price = item_data.get('estimated_unit_price', item.estimated_unit_price)
                            item.priority = item_data.get('priority', item.priority)
                            item.estimated_total_cost = item.recommended_quantity * item.estimated_unit_price
                            item.save()
                            updated_item_ids.append(item.id)
                            total_cost += float(item.estimated_total_cost)
                        except MarketProcurementItem.DoesNotExist:
                            continue
                    else:
                        # Create new item
                        product = Product.objects.get(id=item_data['product_id'])
                        estimated_total = float(item_data['recommended_quantity']) * float(item_data['estimated_unit_price'])
                        
                        item = MarketProcurementItem.objects.create(
                            recommendation=recommendation,
                            product=product,
                            needed_quantity=item_data['needed_quantity'],
                            recommended_quantity=item_data['recommended_quantity'],
                            estimated_unit_price=item_data['estimated_unit_price'],
                            estimated_total_cost=estimated_total,
                            priority=item_data.get('priority', 'medium'),
                            reasoning=item_data.get('reasoning', f'Updated item for {product.name}')
                        )
                        updated_item_ids.append(item.id)
                        total_cost += estimated_total
                
                # Remove items that weren't included in the update
                recommendation.items.exclude(id__in=updated_item_ids).delete()
                
                # Update total cost
                recommendation.total_estimated_cost = total_cost
                recommendation.items_count = len(updated_item_ids)
            
            recommendation.save()
        
        return Response({
            'success': True,
            'message': 'Recommendation updated successfully',
            'recommendation': MarketProcurementRecommendationSerializer(recommendation).data
        })
        
    except MarketProcurementRecommendation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recommendation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating recommendation: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_procurement_buffers(request):
    """
    Get procurement buffer settings for all products
    
    GET /api/products/procurement/buffers/
    """
    try:
        buffers = ProcurementBuffer.objects.select_related('product', 'product__department').all()
        serializer = ProcurementBufferSerializer(buffers, many=True)
        
        return Response({
            'success': True,
            'buffers': serializer.data,
            'count': buffers.count()
        })
        
    except Exception as e:
        logger.error(f"Error fetching procurement buffers: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_procurement_buffer(request, product_id):
    """
    Update procurement buffer settings for a product
    
    POST /api/products/procurement/buffers/{product_id}/
    Body: {
        "spoilage_rate": 0.15,
        "cutting_waste_rate": 0.10,
        "quality_rejection_rate": 0.05,
        "market_pack_size": 5.0,
        "market_pack_unit": "kg",
        "is_seasonal": false,
        "peak_season_months": [11, 12, 1, 2],
        "peak_season_buffer_multiplier": 1.5
    }
    """
    try:
        product = Product.objects.get(id=product_id)
        
        # Get or create buffer
        buffer, created = ProcurementBuffer.objects.get_or_create(
            product=product,
            defaults={
                'spoilage_rate': 0.15,
                'cutting_waste_rate': 0.10,
                'quality_rejection_rate': 0.05
            }
        )
        
        # Update buffer with request data
        serializer = ProcurementBufferSerializer(buffer, data=request.data, partial=True)
        if serializer.is_valid():
            old_total = float(buffer.total_buffer_rate)
            serializer.save()
            new_total = float(buffer.total_buffer_rate)
            
            print(f"🔧 Updated buffer for {product.name}: {old_total:.1%} → {new_total:.1%}")
            print(f"   Spoilage: {float(buffer.spoilage_rate):.1%}, Cutting: {float(buffer.cutting_waste_rate):.1%}, Quality: {float(buffer.quality_rejection_rate):.1%}")
            print(f"   Market pack: {float(buffer.market_pack_size)}, Seasonal: {buffer.is_seasonal}")
            
            return Response({
                'success': True,
                'message': f'Updated procurement buffer for {product.name}',
                'buffer': serializer.data
            })
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating procurement buffer: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_recipes(request):
    """
    Get all product recipes
    
    GET /api/products/procurement/recipes/
    """
    try:
        recipes = Recipe.objects.select_related('product').all()
        serializer = RecipeSerializer(recipes, many=True)
        
        return Response({
            'success': True,
            'recipes': serializer.data,
            'count': recipes.count()
        })
        
    except Exception as e:
        logger.error(f"Error fetching recipes: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_veggie_box_recipes(request):
    """
    Create sample veggie box recipes
    
    POST /api/products/procurement/recipes/create-veggie-boxes/
    """
    try:
        created_recipes = RecipeService.create_veggie_box_recipes()
        
        return Response({
            'success': True,
            'message': f'Created {len(created_recipes)} veggie box recipes',
            'recipes_created': [recipe.product.name for recipe in created_recipes]
        })
        
    except Exception as e:
        logger.error(f"Error creating veggie box recipes: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def manage_product_recipe(request, product_id):
    """
    Get, create, or update recipe for a specific product
    
    GET /api/products/procurement/recipes/product/{product_id}/
    POST /api/products/procurement/recipes/product/{product_id}/
    PUT /api/products/procurement/recipes/product/{product_id}/
    
    Body (POST/PUT):
    {
        "ingredients": [
            {"product_id": 123, "quantity": 10.0},
            {"product_id": 456, "quantity": 2.5}
        ],
        "instructions": "Recipe instructions",
        "prep_time_minutes": 30,
        "yield_quantity": 1,
        "yield_unit": "box"
    }
    """
    try:
        product = Product.objects.get(id=product_id)
        
        if request.method == 'GET':
            # Get recipe for product
            try:
                recipe = Recipe.objects.get(product=product)
                serializer = RecipeSerializer(recipe)
                return Response({
                    'success': True,
                    'recipe': serializer.data
                })
            except Recipe.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'No recipe found for this product'
                }, status=status.HTTP_404_NOT_FOUND)
        
        elif request.method == 'POST' or request.method == 'PUT':
            # Create or update recipe
            ingredients = request.data.get('ingredients', [])
            instructions = request.data.get('instructions', '')
            prep_time_minutes = request.data.get('prep_time_minutes', 30)
            yield_quantity = request.data.get('yield_quantity', 1)
            yield_unit = request.data.get('yield_unit', 'piece')
            
            # Validate ingredients structure (minimal: product_id + quantity)
            validated_ingredients = []
            for ingredient in ingredients:
                if 'product_id' not in ingredient or 'quantity' not in ingredient:
                    return Response({
                        'success': False,
                        'error': 'Each ingredient must have product_id and quantity'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Verify product exists
                try:
                    ingredient_product = Product.objects.get(id=ingredient['product_id'])
                    validated_ingredient = {
                        'product_id': ingredient_product.id,
                        'quantity': float(ingredient['quantity'])
                    }
                    # Optional: Add product_name and unit for convenience
                    validated_ingredient['product_name'] = ingredient_product.name
                    validated_ingredient['unit'] = ingredient_product.unit
                    validated_ingredients.append(validated_ingredient)
                except Product.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': f"Product {ingredient['product_id']} not found"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create or update recipe
            recipe, created = Recipe.objects.update_or_create(
                product=product,
                defaults={
                    'ingredients': validated_ingredients,
                    'instructions': instructions,
                    'prep_time_minutes': prep_time_minutes,
                    'yield_quantity': yield_quantity,
                    'yield_unit': yield_unit
                }
            )
            
            serializer = RecipeSerializer(recipe)
            return Response({
                'success': True,
                'message': f'Recipe {"created" if created else "updated"} successfully',
                'recipe': serializer.data
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error managing product recipe: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def procurement_dashboard_data(request):
    """
    Get comprehensive procurement dashboard data for Karl
    
    GET /api/products/procurement/dashboard/
    """
    try:
        # Get recent recommendations
        recent_recommendations = MarketProcurementRecommendation.objects.filter(
            for_date__gte=timezone.now().date() - timedelta(days=7)
        ).order_by('-created_at')[:5]
        
        # Get critical stock items
        critical_buffers = ProcurementBuffer.objects.select_related('product').filter(
            product__inventory__available_quantity__lte=0
        )[:10]
        
        # Get products with recipes
        products_with_recipes = Recipe.objects.select_related('product').count()
        
        # Calculate total procurement value (last 30 days)
        total_procurement_value = MarketProcurementRecommendation.objects.filter(
            for_date__gte=timezone.now().date() - timedelta(days=30),
            status='purchased'
        ).aggregate(total=models.Sum('total_estimated_cost'))['total'] or 0
        
        # Serialize data
        recommendations_serializer = MarketProcurementRecommendationSerializer(recent_recommendations, many=True)
        buffers_serializer = ProcurementBufferSerializer(critical_buffers, many=True)
        
        return Response({
            'success': True,
            'dashboard_data': {
                'recent_recommendations': recommendations_serializer.data,
                'critical_stock_items': buffers_serializer.data,
                'products_with_recipes': products_with_recipes,
                'total_procurement_value_30d': float(total_procurement_value),
                'recommendations_count': recent_recommendations.count(),
                'critical_items_count': critical_buffers.count()
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching procurement dashboard data: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_market_recommendation(request, recommendation_id):
    """
    Generate printable market trip list for approved recommendation
    
    GET /api/products/procurement/recommendations/{id}/print/
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        
        if recommendation.status != 'approved':
            return Response({
                'success': False,
                'error': f'Can only print approved recommendations. Current status: {recommendation.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get procurement items
        items = recommendation.items.all().order_by('priority', 'product__name')
        
        # Generate printable data
        print_data = {
            'recommendation_id': recommendation.id,
            'trip_date': recommendation.for_date.strftime('%A, %B %d, %Y'),
            'approved_by': recommendation.approved_by.get_full_name() if recommendation.approved_by else 'Unknown',
            'approved_at': recommendation.approved_at.strftime('%Y-%m-%d %H:%M') if recommendation.approved_at else '',
            'total_cost': float(recommendation.total_estimated_cost),
            'total_items': items.count(),
            'items': []
        }
        
        # Add items with priority grouping
        priority_order = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
        
        for item in items:
            print_data['items'].append({
                'product_name': item.product.name,
                'needed_quantity': float(item.needed_quantity),
                'recommended_quantity': float(item.recommended_quantity),
                'unit': item.product.unit,
                'estimated_price': float(item.estimated_unit_price),
                'estimated_total': float(item.estimated_total_cost),
                'priority': item.priority,
                'priority_order': priority_order.get(item.priority, 5),
                'reasoning': item.reasoning,
                'department': item.product.department.name if item.product.department else 'General'
            })
        
        # Group by priority for better printing
        from itertools import groupby
        grouped_items = {}
        for priority, group in groupby(print_data['items'], key=lambda x: x['priority']):
            grouped_items[priority] = list(group)
        
        print_data['grouped_items'] = grouped_items
        
        return Response({
            'success': True,
            'print_data': print_data
        })
        
    except MarketProcurementRecommendation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recommendation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_market_recommendation(request, recommendation_id):
    """
    Delete a market procurement recommendation
    
    DELETE /api/products/procurement/recommendations/{id}/delete/
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        
        # Store info for response
        recommendation_info = {
            'id': recommendation.id,
            'for_date': recommendation.for_date.strftime('%Y-%m-%d'),
            'status': recommendation.status,
            'total_cost': float(recommendation.total_estimated_cost)
        }
        
        # Delete the recommendation (this will cascade delete related items)
        recommendation.delete()
        
        return Response({
            'success': True,
            'message': f'Market recommendation for {recommendation_info["for_date"]} deleted successfully',
            'deleted_recommendation': recommendation_info
        })
        
    except MarketProcurementRecommendation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recommendation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_procurement_item_quantity(request, recommendation_id, item_id):
    """
    Update the quantity of a specific procurement item
    
    PATCH /api/products/procurement/recommendations/{recommendation_id}/items/{item_id}/
    Body: {
        "recommended_quantity": 5.0
    }
    """
    try:
        # Get the recommendation and item
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        item = recommendation.items.get(id=item_id)
        
        # Only allow editing pending recommendations
        if recommendation.status != 'pending':
            return Response({
                'success': False,
                'error': f'Cannot edit {recommendation.status} recommendations. Only pending recommendations can be modified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get new quantity from request
        new_quantity = request.data.get('recommended_quantity')
        if new_quantity is None:
            return Response({
                'success': False,
                'error': 'recommended_quantity is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            new_quantity = float(new_quantity)
            if new_quantity <= 0:
                return Response({
                    'success': False,
                    'error': 'Quantity must be greater than 0'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'success': False,
                'error': 'Invalid quantity format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update the item
        old_quantity = float(item.recommended_quantity)
        old_total = float(item.estimated_total_cost)
        
        item.recommended_quantity = new_quantity
        item.estimated_total_cost = new_quantity * float(item.estimated_unit_price)
        item.save()
        
        # Recalculate recommendation total
        recommendation.total_estimated_cost = sum(
            float(i.estimated_total_cost) for i in recommendation.items.all()
        )
        recommendation.save()
        
        # Serialize the updated item
        from .serializers import MarketProcurementItemSerializer
        item_serializer = MarketProcurementItemSerializer(item)
        
        return Response({
            'success': True,
            'message': f'Updated {item.product.name} quantity from {old_quantity} to {new_quantity}',
            'item': item_serializer.data,
            'recommendation_total': float(recommendation.total_estimated_cost),
            'changes': {
                'old_quantity': old_quantity,
                'new_quantity': new_quantity,
                'old_total': old_total,
                'new_total': float(item.estimated_total_cost)
            }
        })
        
    except MarketProcurementRecommendation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recommendation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except MarketProcurementItem.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Procurement item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_procurement_by_supplier(request, recommendation_id):
    """
    Get procurement recommendation grouped by supplier
    
    GET /api/products/procurement/recommendations/{id}/by-supplier/
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        
        # Refresh from database to ensure we have latest data
        recommendation.refresh_from_db()
        
        # Group items by supplier
        supplier_groups = {}
        items_without_supplier = []
        
        # Force fresh query - check reserved stock first, then split between Fambri Garden and supplier (if needed)
        for item in recommendation.items.select_related('product', 'product__procurement_supplier').all():
            from decimal import Decimal
            # Load inventory to determine reserved quantity
            reserved_qty = Decimal('0')
            try:
                from inventory.models import FinishedInventory
                inventory = FinishedInventory.objects.get(product=item.product)
                reserved_qty = Decimal(str(inventory.reserved_quantity or 0))
            except FinishedInventory.DoesNotExist:
                pass

            # Determine split quantities
            recommended_qty = Decimal(str(item.recommended_quantity or 0))
            reserved_for_pdf = min(reserved_qty, recommended_qty)
            supplier_qty = recommended_qty - reserved_for_pdf

            # Helper to clone serialized item with adjusted qty and total
            def _item_with_qty(base_data, new_qty_decimal):
                data = dict(base_data)
                # Ensure numeric types are computed correctly
                unit_price = Decimal(str(data.get('estimated_unit_price') if data.get('estimated_unit_price') is not None else (item.estimated_unit_price or 0)))
                new_total = unit_price * new_qty_decimal
                data['recommended_quantity'] = float(new_qty_decimal)
                data['estimated_total_cost'] = float(new_total)
                return data

            # Serialize once as base
            from .serializers import MarketProcurementItemSerializer
            base_item_data = MarketProcurementItemSerializer(item).data

            # If there is a reserved portion, add ONLY that to Fambri Garden (NULL supplier)
            if reserved_for_pdf > 0:
                reserved_item = _item_with_qty(base_item_data, reserved_for_pdf)
                print(f"[SUPPLIER VIEW - SPLIT] {item.product.name}: Reserved {reserved_for_pdf} → Fambri Garden")
                items_without_supplier.append(reserved_item)
                
                # CRITICAL: If we have ANY reserved stock, DO NOT add remaining to external supplier
                # Reserved stock means we already have it - external supplier should only get non-reserved shortfall
                # Skip the rest of this item entirely - it's already covered by reserved stock
                continue

            # No reserved stock - handle normal procurement assignment
            assigned_supplier = item.product.procurement_supplier if supplier_qty > 0 else None

            if assigned_supplier and supplier_qty > 0:
                supplier_id = assigned_supplier.id
                supplier_name = assigned_supplier.name

                if supplier_id not in supplier_groups:
                    supplier_groups[supplier_id] = {
                        'supplier_id': supplier_id,
                        'supplier_name': supplier_name,
                        'items': [],
                        'total_cost': 0,
                        'item_count': 0
                    }

                supplier_item = _item_with_qty(base_item_data, supplier_qty)
                print(f"[SUPPLIER VIEW - SPLIT] {item.product.name}: Supplier {supplier_name} qty {supplier_qty}")
                supplier_groups[supplier_id]['items'].append(supplier_item)
                supplier_groups[supplier_id]['total_cost'] += float(supplier_item['estimated_total_cost'])
                supplier_groups[supplier_id]['item_count'] += 1

            # If no assigned supplier and there is remaining qty, it remains as Fambri Garden
            if not assigned_supplier and supplier_qty > 0:
                remaining_item = _item_with_qty(base_item_data, supplier_qty)
                print(f"[SUPPLIER VIEW - SPLIT] {item.product.name}: No supplier set, remaining {supplier_qty} → Fambri Garden")
                items_without_supplier.append(remaining_item)
        
        # Convert to list and sort by total cost (highest first)
        supplier_list = list(supplier_groups.values())
        supplier_list.sort(key=lambda x: x['total_cost'], reverse=True)
        
        # Add Fambri garden group if there are items without assigned suppliers
        if items_without_supplier:
            fambri_group = {
                'supplier_id': None,
                'supplier_name': 'Fambri Garden',
                'items': items_without_supplier,
                'total_cost': sum(float(item['estimated_total_cost']) for item in items_without_supplier),
                'item_count': len(items_without_supplier)
            }
            supplier_list.append(fambri_group)
        
        return Response({
            'success': True,
            'recommendation': {
                'id': recommendation.id,
                'for_date': recommendation.for_date.strftime('%Y-%m-%d'),
                'status': recommendation.status,
                'total_estimated_cost': float(recommendation.total_estimated_cost),
                'created_at': recommendation.created_at.isoformat(),
                'approved_at': recommendation.approved_at.isoformat() if recommendation.approved_at else None,
                'approved_by': recommendation.approved_by.username if recommendation.approved_by else None,
            },
            'suppliers': supplier_list,
            'total_suppliers': len(supplier_list),
            'total_items': sum(group['item_count'] for group in supplier_list)
        })
        
    except MarketProcurementRecommendation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recommendation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_procurement_item_supplier(request, recommendation_id, item_id):
    """
    Update supplier for a specific procurement item
    
    PUT /api/products/procurement/recommendations/{id}/items/{item_id}/supplier/
    Body: {"supplier_id": 123}
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        item = recommendation.items.get(id=item_id)
        
        supplier_id = request.data.get('supplier_id')
        
        if supplier_id:
            from suppliers.models import Supplier
            supplier = Supplier.objects.get(id=supplier_id)
            # Update the product's procurement supplier (permanent change)
            item.product.procurement_supplier = supplier
            item.product.save(update_fields=['procurement_supplier'])
        else:
            # Set to NULL (Fambri garden)
            item.product.procurement_supplier = None
            item.product.save(update_fields=['procurement_supplier'])
        
        return Response({
            'success': True,
            'message': f'Supplier updated for {item.product.name}',
            'item': {
                'id': item.id,
                'product_name': item.product.name,
                'new_supplier': supplier.name if supplier_id else 'Fambri Garden'
            }
        })
        
    except (MarketProcurementRecommendation.DoesNotExist, MarketProcurementItem.DoesNotExist):
        return Response({
            'success': False,
            'error': 'Recommendation or item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def bulk_update_procurement_suppliers(request, recommendation_id):
    """
    Bulk update suppliers for multiple procurement items
    
    PUT /api/products/procurement/recommendations/{id}/bulk-supplier-update/
    Body: {
        "updates": [
            {"item_id": 1, "supplier_id": 123},
            {"item_id": 2, "supplier_id": null}
        ]
    }
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        updates = request.data.get('updates', [])
        
        if not updates:
            return Response({
                'success': False,
                'error': 'No updates provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from suppliers.models import Supplier
        updated_items = []
        errors = []
        
        for update in updates:
            try:
                item_id = update.get('item_id')
                supplier_id = update.get('supplier_id')
                
                item = recommendation.items.get(id=item_id)
                
                if supplier_id:
                    supplier = Supplier.objects.get(id=supplier_id)
                    item.product.procurement_supplier = supplier
                    supplier_name = supplier.name
                else:
                    item.product.procurement_supplier = None
                    supplier_name = 'Fambri Garden'
                
                item.product.save(update_fields=['procurement_supplier'])
                
                updated_items.append({
                    'item_id': item.id,
                    'product_name': item.product.name,
                    'new_supplier': supplier_name
                })
                
            except Exception as e:
                errors.append({
                    'item_id': update.get('item_id'),
                    'error': str(e)
                })
        
        return Response({
            'success': True,
            'updated_count': len(updated_items),
            'updated_items': updated_items,
            'errors': errors
        })
        
    except MarketProcurementRecommendation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Recommendation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_suppliers(request):
    """
    Get all available suppliers for supplier selection
    
    GET /api/products/suppliers/
    """
    try:
        from suppliers.models import Supplier
        
        suppliers = Supplier.objects.filter(
            is_active=True
        ).values('id', 'name', 'contact_person', 'phone').order_by('name')
        
        # Add Fambri Garden as NULL option
        supplier_list = [
            {
                'id': None,
                'name': 'Fambri Garden',
                'contact_person': 'Internal',
                'phone': '-'
            }
        ]
        supplier_list.extend(list(suppliers))
        
        return Response({
            'success': True,
            'suppliers': supplier_list
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

