from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .models import (
    SystemSetting, CustomerSegment, OrderStatus, 
    StockAdjustmentType, BusinessConfiguration
)
from products.models import Department, Product


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_customer_segments(request):
    """Get all active customer segments"""
    segments = CustomerSegment.objects.filter(is_active=True).values(
        'id', 'name', 'description', 'default_markup', 
        'credit_limit_multiplier', 'payment_terms_days'
    )
    return Response(list(segments))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_statuses(request):
    """Get all active order statuses"""
    statuses = OrderStatus.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 
        'color', 'is_final', 'sort_order'
    )
    return Response(list(statuses))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_adjustment_types(request):
    """Get all active stock adjustment types"""
    types = StockAdjustmentType.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 
        'affects_cost', 'requires_reason'
    )
    return Response(list(types))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_departments(request):
    """Get all active product departments"""
    departments = Department.objects.filter(is_active=True).values(
        'id', 'name', 'description'
    )
    return Response(list(departments))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_units_of_measure(request):
    """Get all unique units of measure from products"""
    units = Product.objects.filter(is_active=True).values_list('unit', flat=True).distinct()
    units_list = [{'value': unit, 'label': unit} for unit in units if unit]
    return Response(units_list)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_business_configuration(request):
    """Get all business configuration settings"""
    configs = {}
    for config in BusinessConfiguration.objects.filter(is_active=True):
        configs[config.name] = {
            'value': config.get_value(),
            'display_name': config.display_name,
            'description': config.description,
            'category': config.category,
            'type': config.value_type
        }
    return Response(configs)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_system_settings(request):
    """Get system settings by category"""
    category = request.GET.get('category', 'general')
    settings = SystemSetting.objects.filter(
        category=category, 
        is_active=True
    ).values('key', 'value', 'description')
    
    settings_dict = {setting['key']: setting['value'] for setting in settings}
    return Response(settings_dict)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_form_options(request):
    """Get all form options in one call for efficiency"""
    return Response({
        'customer_segments': list(CustomerSegment.objects.filter(is_active=True).values(
            'id', 'name', 'description'
        )),
        'order_statuses': list(OrderStatus.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'color'
        )),
        'adjustment_types': list(StockAdjustmentType.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description'
        )),
        'departments': list(Department.objects.filter(is_active=True).values(
            'id', 'name', 'description'
        )),
        'units_of_measure': [
            {'value': unit, 'label': unit} 
            for unit in Product.objects.filter(is_active=True).values_list('unit', flat=True).distinct() 
            if unit
        ],
        'customer_types': [
            {'value': 'restaurant', 'label': 'Restaurant'},
            {'value': 'private', 'label': 'Private Customer'},
            {'value': 'internal', 'label': 'Internal'},
            {'value': 'wholesale', 'label': 'Wholesale'},
        ],
        'payment_terms': [
            {'value': 0, 'label': 'Cash on Delivery'},
            {'value': 7, 'label': '7 Days'},
            {'value': 14, 'label': '14 Days'},
            {'value': 30, 'label': '30 Days'},
            {'value': 60, 'label': '60 Days'},
        ],
        'priority_levels': [
            {'value': 'low', 'label': 'Low', 'color': '#28a745'},
            {'value': 'normal', 'label': 'Normal', 'color': '#007bff'},
            {'value': 'high', 'label': 'High', 'color': '#ffc107'},
            {'value': 'urgent', 'label': 'Urgent', 'color': '#dc3545'},
        ]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_business_config(request):
    """Update business configuration values"""
    try:
        for key, value in request.data.items():
            config = BusinessConfiguration.objects.get(name=key, is_active=True)
            config.set_value(value)
            config.save()
        
        return Response({'message': 'Configuration updated successfully'})
    except BusinessConfiguration.DoesNotExist:
        return Response(
            {'error': f'Configuration key "{key}" not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
