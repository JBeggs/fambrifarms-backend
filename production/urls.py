from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# For future API endpoints
router = DefaultRouter()
# router.register(r'recipes', views.RecipeViewSet)
# router.register(r'production-batches', views.ProductionBatchViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Recipe endpoints - single endpoint handles GET/POST/PUT/DELETE
    path('products/<int:product_id>/recipe/', views.product_recipe_detail, name='product-recipe-detail'),
    path('recipes/', views.list_recipes, name='list-recipes'),
]
