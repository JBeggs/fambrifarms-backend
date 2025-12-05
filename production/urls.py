from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# For future API endpoints
router = DefaultRouter()
# router.register(r'recipes', views.RecipeViewSet)
# router.register(r'production-batches', views.ProductionBatchViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Recipe endpoints
    path('products/<int:product_id>/recipe/', views.get_product_recipe, name='get-product-recipe'),
    path('recipes/', views.list_recipes, name='list-recipes'),
]
