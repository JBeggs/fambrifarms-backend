from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order_list'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    # Alias to match API overview
    path('<int:order_id>/status/', views.update_order_status, name='order_status'),
    # WhatsApp integration endpoint
    path('from-whatsapp/', views.create_order_from_whatsapp, name='create_order_from_whatsapp'),
    # Customer orders endpoint
    path('customer/<int:customer_id>/', views.CustomerOrdersView.as_view(), name='customer_orders'),
] 