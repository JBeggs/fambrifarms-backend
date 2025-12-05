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


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
@permission_classes([AllowAny if 'GET' else IsAuthenticated])  # GET is public, others require auth
def product_recipe_detail(request, product_id):
    """
    Handle recipe operations for a product
    
    GET: Get recipe (if exists)
    POST: Create new recipe
    PUT: Update existing recipe
    DELETE: Deactivate recipe
    """
    try:
        product = get_object_or_404(Product, id=product_id)
        
        if request.method == 'GET':
            # Get recipe
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
        
        elif request.method == 'DELETE':
            # Deactivate recipe
            recipe = Recipe.objects.filter(product=product).first()
            if not recipe:
                return Response({
                    'status': 'error',
                    'message': 'Recipe not found for this product'
                }, status=status.HTTP_404_NOT_FOUND)
            
            recipe.is_active = False
            recipe.save()
            
            return Response({
                'status': 'success',
                'message': 'Recipe deactivated successfully'
            })
        
        elif request.method in ['POST', 'PUT']:
            # Create or update recipe
            from django.db import transaction
            
            # Validate required fields
            name = request.data.get('name', f'Recipe for {product.name}')
            ingredients_data = request.data.get('ingredients', [])
            
            if not ingredients_data:
                return Response({
                    'status': 'error',
                    'message': 'At least one ingredient is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Get or create recipe
                recipe, created = Recipe.objects.get_or_create(
                    product=product,
                    defaults={
                        'name': name,
                        'description': request.data.get('description', ''),
                        'batch_size': request.data.get('batch_size', 1),
                        'production_time_minutes': request.data.get('production_time_minutes', 60),
                        'yield_percentage': request.data.get('yield_percentage', 100.0),
                        'is_active': request.data.get('is_active', True),
                        'version': request.data.get('version', '1.0'),
                    }
                )
                
                # Update if existing
                if not created:
                    recipe.name = name
                    recipe.description = request.data.get('description', '')
                    recipe.batch_size = request.data.get('batch_size', recipe.batch_size)
                    recipe.production_time_minutes = request.data.get('production_time_minutes', recipe.production_time_minutes)
                    recipe.yield_percentage = request.data.get('yield_percentage', recipe.yield_percentage)
                    recipe.is_active = request.data.get('is_active', recipe.is_active)
                    recipe.version = request.data.get('version', recipe.version)
                    recipe.save()
                
                # Clear existing ingredients
                RecipeIngredient.objects.filter(recipe=recipe).delete()
                
                # Create new ingredients
                for ing_data in ingredients_data:
                    raw_material_id = ing_data.get('raw_material_id') or ing_data.get('product_id')
                    if not raw_material_id:
                        return Response({
                            'status': 'error',
                            'message': 'Each ingredient must have raw_material_id or product_id'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    try:
                        raw_material = Product.objects.get(id=raw_material_id)
                    except Product.DoesNotExist:
                        return Response({
                            'status': 'error',
                            'message': f'Ingredient product with ID {raw_material_id} not found'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    quantity = ing_data.get('quantity', 0)
                    if quantity <= 0:
                        return Response({
                            'status': 'error',
                            'message': f'Ingredient quantity must be greater than 0 for {raw_material.name}'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        raw_material=raw_material,
                        quantity=quantity,
                        unit=ing_data.get('unit') or raw_material.unit,
                        preparation_notes=ing_data.get('preparation_notes', ''),
                        is_optional=ing_data.get('is_optional', False),
                    )
                
                # Reload recipe with ingredients
                recipe.refresh_from_db()
                serializer = RecipeSerializer(recipe)
                
                return Response({
                    'status': 'success',
                    'message': 'Recipe created successfully' if created else 'Recipe updated successfully',
                    'recipe': serializer.data
                })
            
    except Product.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error handling recipe for product {product_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({
            'status': 'error',
            'message': 'Failed to process recipe request',
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


