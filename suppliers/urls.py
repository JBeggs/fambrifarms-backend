from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API endpoints
router = DefaultRouter()
router.register(r'suppliers', views.SupplierViewSet, basename='supplier')
router.register(r'sales-reps', views.SalesRepViewSet, basename='salesrep')
router.register(r'supplier-products', views.SupplierProductViewSet, basename='supplierproduct')

urlpatterns = [
    path('', include(router.urls)),
    
    # Supplier Performance Tracking APIs
    path('performance/<int:supplier_id>/', views.get_supplier_performance, name='get_supplier_performance'),
    path('performance/rankings/', views.get_supplier_rankings, name='get_supplier_rankings'),
    path('performance/dashboard/', views.get_performance_dashboard, name='get_performance_dashboard'),
]
