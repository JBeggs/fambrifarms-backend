from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'supplier-products', views.SupplierProductViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),
    
    # Summary and analytics endpoints
    path('summary/', views.supplier_summary, name='supplier-summary'),
    path('best-prices/', views.best_prices, name='best-prices'),
] 