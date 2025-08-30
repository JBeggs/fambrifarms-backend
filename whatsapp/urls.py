from django.urls import path
from . import views

urlpatterns = [
    # WhatsApp message processing
    path('messages/', views.WhatsAppMessageListView.as_view(), name='whatsapp-messages'),
    path('messages/<int:pk>/', views.WhatsAppMessageDetailView.as_view(), name='whatsapp-message-detail'),
    path('messages/receive/', views.receive_whatsapp_message, name='receive-whatsapp-message'),
    path('messages/parse/<int:message_id>/', views.parse_whatsapp_message, name='parse-whatsapp-message'),
    path('messages/confirm-parsing/<int:message_id>/', views.confirm_parsing, name='confirm-parsing'),
    
    # Sales rep management
    path('sales-reps/', views.SalesRepListView.as_view(), name='sales-reps'),
    path('sales-reps/<int:pk>/', views.SalesRepDetailView.as_view(), name='sales-rep-detail'),
    
    # Purchase orders
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase-orders'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('purchase-orders/generate/', views.generate_purchase_order, name='generate-purchase-order'),
    path('purchase-orders/<int:po_id>/send/', views.send_po_to_sales_rep, name='send-po-to-sales-rep'),
]
