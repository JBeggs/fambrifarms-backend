from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order_list'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    # Alias to match API overview
    path('<int:order_id>/status/', views.update_order_status, name='order_status'),
    # Order locking endpoints
    path('<int:order_id>/lock/', views.lock_order, name='lock_order'),
    path('<int:order_id>/unlock/', views.unlock_order, name='unlock_order'),
    # WhatsApp integration endpoint
    path('from-whatsapp/', views.create_order_from_whatsapp, name='create_order_from_whatsapp'),
    # Customer orders endpoint
    path('customer/<int:customer_id>/', views.CustomerOrdersView.as_view(), name='customer_orders'),
    # Order item management endpoints
    path('<int:order_id>/items/', views.add_order_item, name='add_order_item'),
    path('<int:order_id>/items/<int:item_id>/', views.order_item_detail, name='order_item_detail'),
] 