from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# For future API endpoints
router = DefaultRouter()
# router.register(r'recipes', views.RecipeViewSet)
# router.register(r'production-batches', views.ProductionBatchViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add specific endpoints here as needed
]
