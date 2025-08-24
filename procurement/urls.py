from django.urls import path
from . import views

urlpatterns = [
    path('purchase-orders/generate/', views.generate_pos_from_order),
    path('purchase-orders/<int:po_id>/', views.purchase_order_detail),
    path('purchase-orders/<int:po_id>/receive/', views.receive_purchase_order),
]
