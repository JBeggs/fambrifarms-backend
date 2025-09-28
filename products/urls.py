from django.urls import path
from . import views, views_procurement

urlpatterns = [
    path('', views.api_overview, name='products_api_overview'),
    path('app-config/', views.app_config, name='app_config'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:product_id>/customer-price/', views.get_customer_price, name='get_customer_price'),
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('alerts/', views.product_alerts, name='product_alerts'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Procurement Intelligence APIs
    path('procurement/generate-recommendation/', views_procurement.generate_market_recommendation, name='generate_market_recommendation'),
    path('procurement/recommendations/', views_procurement.get_market_recommendations, name='get_market_recommendations'),
    path('procurement/recommendations/<int:recommendation_id>/approve/', views_procurement.approve_market_recommendation, name='approve_market_recommendation'),
    path('procurement/buffers/', views_procurement.get_procurement_buffers, name='get_procurement_buffers'),
    path('procurement/buffers/<int:product_id>/', views_procurement.update_procurement_buffer, name='update_procurement_buffer'),
    path('procurement/recipes/', views_procurement.get_product_recipes, name='get_product_recipes'),
    path('procurement/recipes/create-veggie-boxes/', views_procurement.create_veggie_box_recipes, name='create_veggie_box_recipes'),
    path('procurement/dashboard/', views_procurement.procurement_dashboard_data, name='procurement_dashboard_data'),
]