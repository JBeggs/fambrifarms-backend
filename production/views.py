from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Recipe, RecipeIngredient
from .serializers import RecipeSerializer, RecipeIngredientSerializer
from products.models import Product
import logging

logger = logging.getLogger('production')


@api_view(['GET'])
@permission_classes([AllowAny])  # Allow access for order creation flow
def get_product_recipe(request, product_id):
    """
    Get recipe for a specific product (if it exists)
    
    Returns:
    - Recipe with ingredients if recipe exists
    - null if no recipe exists
    """
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product has an active recipe
        recipe = Recipe.objects.filter(
            product=product,
            is_active=True
        ).select_related('product').prefetch_related(
            'ingredients__raw_material'
        ).first()
        
        if recipe:
            serializer = RecipeSerializer(recipe)
            return Response({
                'status': 'success',
                'recipe': serializer.data
            })
        else:
            # No recipe exists - return null (not an error)
            return Response({
                'status': 'success',
                'recipe': None
            })
            
    except Product.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching recipe for product {product_id}: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Failed to fetch recipe',
            'details': str(e) if request.user.is_authenticated and request.user.is_staff else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_recipes(request):
    """
    List all active recipes (admin/management endpoint)
    """
    try:
        recipes = Recipe.objects.filter(
            is_active=True
        ).select_related('product').prefetch_related(
            'ingredients__raw_material'
        ).order_by('product__name')
        
        serializer = RecipeSerializer(recipes, many=True)
        return Response({
            'status': 'success',
            'recipes': serializer.data,
            'count': len(serializer.data)
        })
    except Exception as e:
        logger.error(f"Error listing recipes: {str(e)}")
        return Response({
            'status': 'error',
            'message': 'Failed to list recipes',
            'details': str(e) if request.user.is_staff else None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
