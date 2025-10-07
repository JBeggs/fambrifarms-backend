from django.urls import path
from . import views

urlpatterns = [
    # Health check
    path('health/', views.health_check, name='whatsapp-health'),
    
    # Companies
    path('companies/', views.get_companies, name='get-companies'),
    
    # Message processing
    path('receive-messages/', views.receive_messages, name='receive-messages'),
    path('receive-html/', views.receive_html_messages, name='receive-html-messages'),  # New simplified endpoint
    path('messages/', views.get_messages, name='get-messages'),
    path('messages/edit/', views.edit_message, name='edit-message'),
    path('messages/update-company/', views.update_message_company, name='update-message-company'),
    path('messages/update-type/', views.update_message_type, name='update-message-type'),
    path('messages/process/', views.process_messages_to_orders, name='process-messages'),
    path('messages/process-stock/', views.process_stock_messages, name='process-stock-messages'),
    path('messages/<int:message_id>/', views.delete_message, name='delete-message'),
    path('messages/bulk-delete/', views.bulk_delete_messages, name='bulk-delete-messages'),
    
    # Stock management
    path('stock-updates/', views.get_stock_updates, name='stock-updates'),
    path('stock-updates/apply-to-inventory/', views.apply_stock_updates_to_inventory, name='apply-stock-updates-to-inventory'),
    path('stock-take-data/', views.get_stock_take_data, name='get-stock-take-data'),
    path('process-stock-and-apply/', views.process_stock_and_apply_to_inventory, name='process-stock-and-apply'),
    path('orders/<int:order_id>/validate-stock/', views.validate_order_stock, name='validate-order-stock'),
    
    # Logging and monitoring
    path('logs/', views.get_processing_logs, name='processing-logs'),
    
    # Company extraction refresh
    path('messages/refresh-companies/', views.refresh_company_extraction, name='refresh-company-extraction'),
    
    # Message corrections
    path('messages/corrections/', views.update_message_corrections, name='update-message-corrections'),
    path('messages/reprocess/', views.reprocess_message_with_corrections, name='reprocess-message-with-corrections'),
    
    # Always-suggestions processing
    path('messages/process-with-suggestions/', views.process_message_with_suggestions, name='process-message-with-suggestions'),
    path('orders/create-from-suggestions/', views.create_order_from_suggestions, name='create-order-from-suggestions'),
]
