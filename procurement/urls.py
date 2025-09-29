from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# For future API endpoints
router = DefaultRouter()
# router.register(r'purchase-orders', views.PurchaseOrderViewSet)
# router.register(r'receipts', views.PurchaseOrderReceiptViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Simple purchase order creation for Pretoria Market
    path('purchase-orders/create/', views.create_simple_purchase_order, name='create_simple_purchase_order'),
    
    # Fambri-First Procurement Workflow APIs
    path('analyze-order/', views.analyze_order_procurement, name='analyze_order_procurement'),
    path('process-workflow/', views.process_order_workflow, name='process_order_workflow'),
    path('low-stock-recommendations/', views.get_low_stock_recommendations, name='get_low_stock_recommendations'),
]
