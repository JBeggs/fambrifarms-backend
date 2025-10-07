from django.urls import path
from . import views

urlpatterns = [
    # Individual setting endpoints
    path('customer-segments/', views.get_customer_segments, name='customer-segments'),
    path('order-statuses/', views.get_order_statuses, name='order-statuses'),
    path('adjustment-types/', views.get_adjustment_types, name='adjustment-types'),
    path('departments/', views.get_departments, name='departments'),
    path('units-of-measure/', views.get_units_of_measure, name='units-of-measure'),
    path('business-config/', views.get_business_configuration, name='business-config'),
    path('system-settings/', views.get_system_settings, name='system-settings'),
    
    # New configuration endpoints
    path('message-types/', views.get_message_types, name='message-types'),
    path('user-types/', views.get_user_types, name='user-types'),
    path('supplier-types/', views.get_supplier_types, name='supplier-types'),
    path('invoice-statuses/', views.get_invoice_statuses, name='invoice-statuses'),
    path('payment-methods/', views.get_payment_methods, name='payment-methods'),
    path('production-statuses/', views.get_production_statuses, name='production-statuses'),
    path('quality-grades/', views.get_quality_grades, name='quality-grades'),
    path('priority-levels/', views.get_priority_levels, name='priority-levels'),
    path('whatsapp-patterns/', views.get_whatsapp_patterns, name='whatsapp-patterns'),
    path('product-variations/', views.get_product_variations, name='product-variations'),
    path('company-aliases/', views.get_company_aliases, name='company-aliases'),
    
    # Bulk endpoints for efficiency
    path('form-options/', views.get_form_options, name='form-options'),
    path('all-configuration/', views.get_all_configuration, name='all-configuration'),
    
    # Update endpoints
    path('business-config/update/', views.update_business_config, name='update-business-config'),
]
