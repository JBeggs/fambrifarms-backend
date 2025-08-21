from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_wishlist, name='get_wishlist'),
    path('admin/all/', views.get_all_wishlists, name='get_all_wishlists'),
    path('add/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('convert/', views.convert_to_order, name='convert_to_order'),
    path('check-order-day/', views.check_order_day, name='check_order_day'),
] 