"""
WhatsApp app URL configuration
"""
from django.urls import path
from . import views

app_name = 'whatsapp'

urlpatterns = [
    # WhatsApp message processing
    path('receive-message/', views.receive_message, name='receive_message'),
    path('unparsed-messages/', views.get_unparsed_messages, name='unparsed_messages'),
    path('parse-message/<int:message_id>/', views.parse_message, name='parse_message'),
    path('confirm-parsing/<int:message_id>/', views.confirm_parsing, name='confirm_parsing'),
    
    # Purchase Order generation
    path('generate-po/<int:order_id>/', views.generate_po, name='generate_po'),
    path('po-whatsapp-message/<int:po_id>/', views.get_po_whatsapp_message, name='po_whatsapp_message'),
    path('send-po/<int:po_id>/', views.send_po, name='send_po'),
    
    # List views for management
    path('messages/', views.WhatsAppMessageListView.as_view(), name='message_list'),
    path('messages/<int:pk>/', views.WhatsAppMessageDetailView.as_view(), name='message_detail'),
    path('sales-reps/', views.SalesRepListView.as_view(), name='sales_rep_list'),
    path('sales-reps/<int:pk>/', views.SalesRepDetailView.as_view(), name='sales_rep_detail'),
    path('purchase-orders/', views.PurchaseOrderListView.as_view(), name='purchase_order_list'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase_order_detail'),
]
