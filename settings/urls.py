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
    
    # Bulk endpoints for efficiency
    path('form-options/', views.get_form_options, name='form-options'),
    
    # Update endpoints
    path('business-config/update/', views.update_business_config, name='update-business-config'),
]
