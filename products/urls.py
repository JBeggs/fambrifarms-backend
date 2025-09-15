from django.urls import path
from . import views

urlpatterns = [
    path('', views.api_overview, name='products_api_overview'),
    path('app-config/', views.app_config, name='app_config'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('alerts/', views.product_alerts, name='product_alerts'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
]