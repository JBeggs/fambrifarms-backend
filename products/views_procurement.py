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
    Approve a market procurement recommendation
    
    POST /api/products/procurement/recommendations/{id}/approve/
    Body: {
        "notes": "Optional approval notes"
    }
    """
    try:
        recommendation = MarketProcurementRecommendation.objects.get(id=recommendation_id)
        
        if recommendation.status != 'pending':
            return Response({
                'success': False,
                'error': f'Cannot approve recommendation with status: {recommendation.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update recommendation
        recommendation.status = 'approved'
        recommendation.approved_by = request.user
        recommendation.approved_at = timezone.now()
        recommendation.notes = request.data.get('notes', '')
        recommendation.save()
        
        # Serialize response
        serializer = MarketProcurementRecommendationSerializer(recommendation)
        
        return Response({
            'success': True,
            'message': 'Market recommendation approved',
            'recommendation': serializer.data,
            'print_url': f'/api/products/procurement/recommendations/{recommendation_id}/print/'
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
            serializer.save()
            
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
        
        # Force fresh query - use product's assigned procurement supplier
        for item in recommendation.items.select_related('product', 'product__procurement_supplier').all():
            # Use the product's assigned procurement supplier (new system)
            assigned_supplier = item.product.procurement_supplier
            
            if assigned_supplier:
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
                
                # Serialize the item
                from .serializers import MarketProcurementItemSerializer
                item_data = MarketProcurementItemSerializer(item).data
                
                # Debug logging
                print(f"[SUPPLIER VIEW] Item: {item.product.name} → {supplier_name}, Rec Qty: {item.recommended_quantity}, Unit Price: {item.estimated_unit_price}, Total: {item.estimated_total_cost}")
                print(f"[SUPPLIER VIEW] Serialized data: {item_data}")
                
                supplier_groups[supplier_id]['items'].append(item_data)
                supplier_groups[supplier_id]['total_cost'] += float(item.estimated_total_cost)
                supplier_groups[supplier_id]['item_count'] += 1
            else:
                # Items without assigned procurement supplier (NULL = Fambri garden products)
                from .serializers import MarketProcurementItemSerializer
                item_data = MarketProcurementItemSerializer(item).data
                
                # Debug logging for Fambri garden items
                print(f"[SUPPLIER VIEW - FAMBRI GARDEN] Item: {item.product.name} (NULL procurement_supplier), Rec Qty: {item.recommended_quantity}, Unit Price: {item.estimated_unit_price}, Total: {item.estimated_total_cost}")
                print(f"[SUPPLIER VIEW - FAMBRI GARDEN] Serialized data: {item_data}")
                
                items_without_supplier.append(item_data)
        
        # Convert to list and sort by total cost (highest first)
        supplier_list = list(supplier_groups.values())
        supplier_list.sort(key=lambda x: x['total_cost'], reverse=True)
        
        # Add Fambri garden group if there are items without assigned suppliers
        if items_without_supplier:
            fambri_group = {
                'supplier_id': None,
                'supplier_name': 'Fambri Garden (No External Procurement)',
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
