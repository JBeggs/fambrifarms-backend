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
]
