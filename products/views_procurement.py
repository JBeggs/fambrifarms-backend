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
        "for_date": "2025-01-20" (optional, defaults to today)
    }
    """
    try:
        # Parse request data
        for_date_str = request.data.get('for_date')
        if for_date_str:
            for_date = datetime.strptime(for_date_str, '%Y-%m-%d').date()
        else:
            for_date = timezone.now().date()
        
        # Generate recommendation
        service = ProcurementIntelligenceService()
        recommendation = service.generate_market_recommendation(for_date)
        
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
            'recommendation': serializer.data
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
            product__finishedinventory__available_quantity__lte=0
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
