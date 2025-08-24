from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'units', views.UnitOfMeasureViewSet)
router.register(r'raw-materials', views.RawMaterialViewSet)
router.register(r'raw-material-batches', views.RawMaterialBatchViewSet)
router.register(r'recipes', views.ProductionRecipeViewSet)
router.register(r'finished-inventory', views.FinishedInventoryViewSet)
router.register(r'stock-movements', views.StockMovementViewSet)
router.register(r'production-batches', views.ProductionBatchViewSet)
router.register(r'alerts', views.StockAlertViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),
    
    # Dashboard and summary endpoints
    path('dashboard/', views.inventory_dashboard, name='inventory-dashboard'),
    path('stock-levels/', views.stock_levels, name='stock-levels'),
    
    # Action endpoints
    path('actions/reserve-stock/', views.reserve_stock, name='reserve-stock'),
    path('actions/stock-adjustment/', views.stock_adjustment, name='stock-adjustment'),
]
