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
router.register(r'stock-analysis', views.StockAnalysisViewSet)
router.register(r'market-prices', views.MarketPriceViewSet)
router.register(r'procurement-recommendations', views.ProcurementRecommendationViewSet)
router.register(r'price-alerts', views.PriceAlertViewSet)
router.register(r'pricing-rules', views.PricingRuleViewSet)
router.register(r'customer-price-lists', views.CustomerPriceListViewSet)
router.register(r'weekly-reports', views.WeeklyPriceReportViewSet)
router.register(r'enhanced-market-prices', views.EnhancedMarketPriceViewSet, basename='enhanced-market-price')

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
    path('actions/break-down-package/', views.break_down_package_to_kg, name='break-down-package'),
    
    # Invoice processing endpoints
    path('invoice-upload-status/', views.get_invoice_upload_status, name='invoice-upload-status'),
    path('upload-invoice/', views.upload_invoice_photo, name='upload-invoice'),
    path('upload-invoice-with-extracted-data/', views.upload_invoice_with_extracted_data, name='upload-invoice-with-extracted-data'),
    path('pending-invoices/', views.get_pending_invoices, name='pending-invoices'),
    path('process-stock-received/', views.process_stock_received, name='process-stock-received'),
    
    # Stock take status endpoint
    path('stock-take-status/', views.check_stock_take_status, name='stock-take-status'),
    
    # Weight input endpoints
    path('invoice/<int:invoice_id>/extracted-data/', views.get_extracted_invoice_data, name='get-extracted-invoice-data'),
    path('invoice/<int:invoice_id>/update-weights/', views.update_invoice_weights, name='update-invoice-weights'),
    path('invoice/<int:invoice_id>/process-complete/', views.process_invoice_complete, name='process-invoice-complete'),
]
