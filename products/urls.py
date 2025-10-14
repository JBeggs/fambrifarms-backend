from django.urls import path
from . import views
from . import unified_procurement_views, views_procurement, views_business_settings

urlpatterns = [
    path('', views.api_overview, name='products_api_overview'),
    path('app-config/', views.app_config, name='app_config'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/quick-create/', views.quick_create_product, name='quick_create_product'),
    path('products/<int:product_id>/customer-price/', views.get_customer_price, name='get_customer_price'),
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('alerts/', views.product_alerts, name='product_alerts'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Procurement Intelligence APIs
    path('procurement/generate-recommendation/', views_procurement.generate_market_recommendation, name='generate_market_recommendation'),
    path('procurement/recommendations/', views_procurement.get_market_recommendations, name='get_market_recommendations'),
    path('procurement/recommendations/<int:recommendation_id>/', views_procurement.update_market_recommendation, name='update_market_recommendation'),
    path('procurement/recommendations/<int:recommendation_id>/approve/', views_procurement.approve_market_recommendation, name='approve_market_recommendation'),
    path('procurement/recommendations/<int:recommendation_id>/print/', views_procurement.print_market_recommendation, name='print_market_recommendation'),
    path('procurement/recommendations/<int:recommendation_id>/delete/', views_procurement.delete_market_recommendation, name='delete_market_recommendation'),
    path('procurement/recommendations/<int:recommendation_id>/items/<int:item_id>/', views_procurement.update_procurement_item_quantity, name='update_procurement_item_quantity'),
    path('procurement/recommendations/<int:recommendation_id>/by-supplier/', views_procurement.get_procurement_by_supplier, name='get_procurement_by_supplier'),
    path('procurement/buffers/', views_procurement.get_procurement_buffers, name='get_procurement_buffers'),
    path('procurement/buffers/<int:product_id>/', views_procurement.update_procurement_buffer, name='update_procurement_buffer'),
    path('procurement/recipes/', views_procurement.get_product_recipes, name='get_product_recipes'),
    path('procurement/recipes/create-veggie-boxes/', views_procurement.create_veggie_box_recipes, name='create_veggie_box_recipes'),
    path('procurement/dashboard/', views_procurement.procurement_dashboard_data, name='procurement_dashboard_data'),
    
    # Supplier Optimization APIs
    path('supplier-optimization/calculate-split/', views.calculate_supplier_split, name='calculate_supplier_split'),
    path('supplier-optimization/calculate-order/', views.calculate_order_optimization, name='calculate_order_optimization'),
    path('supplier-optimization/recommendations/<int:product_id>/', views.get_supplier_recommendations, name='get_supplier_recommendations'),
    
    # Unified procurement endpoints
    path('unified-procurement/analysis/', unified_procurement_views.unified_procurement_analysis, name='unified_procurement_analysis'),
    path('unified-procurement/dashboard/', unified_procurement_views.unified_procurement_dashboard, name='unified_procurement_dashboard'),
    path('unified-procurement/product-options/', unified_procurement_views.product_procurement_options, name='product_procurement_options'),
    
    # Business Settings APIs
    path('business-settings/', views_business_settings.get_business_settings, name='get_business_settings'),
    path('business-settings/update/', views_business_settings.update_business_settings, name='update_business_settings'),
    path('business-settings/departments/', views_business_settings.get_department_buffer_settings, name='get_department_buffer_settings'),
    path('business-settings/departments/<str:department_name>/', views_business_settings.update_department_buffer_settings, name='update_department_buffer_settings'),
    path('business-settings/reset/', views_business_settings.reset_to_defaults, name='reset_business_settings'),
]