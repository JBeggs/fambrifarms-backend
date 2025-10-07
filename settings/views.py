from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .models import (
    SystemSetting, CustomerSegment, OrderStatus, 
    StockAdjustmentType, BusinessConfiguration,
    UnitOfMeasure, MessageType, UserType, SupplierType,
    InvoiceStatus, PaymentMethod, ProductionStatus,
    QualityGrade, PriorityLevel, WhatsAppPattern,
    ProductVariation, CompanyAlias
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
        'units_of_measure': list(UnitOfMeasure.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'category', 'sort_order'
        )),
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


# New API endpoints for all configuration models

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_units_of_measure(request):
    """Get all active units of measure"""
    units = UnitOfMeasure.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'category', 'sort_order'
    )
    return Response(list(units))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_message_types(request):
    """Get all active message types"""
    types = MessageType.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'color', 'sort_order'
    )
    return Response(list(types))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_types(request):
    """Get all active user types"""
    types = UserType.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'permissions', 'sort_order'
    )
    return Response(list(types))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_supplier_types(request):
    """Get all active supplier types"""
    types = SupplierType.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'sort_order'
    )
    return Response(list(types))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_invoice_statuses(request):
    """Get all active invoice statuses"""
    statuses = InvoiceStatus.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'color', 'is_final', 'sort_order'
    )
    return Response(list(statuses))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_methods(request):
    """Get all active payment methods"""
    methods = PaymentMethod.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'requires_reference', 'sort_order'
    )
    return Response(list(methods))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_production_statuses(request):
    """Get all active production statuses"""
    statuses = ProductionStatus.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'color', 'is_final', 'sort_order'
    )
    return Response(list(statuses))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quality_grades(request):
    """Get all active quality grades"""
    grades = QualityGrade.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'color', 'sort_order'
    )
    return Response(list(grades))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_priority_levels(request):
    """Get all active priority levels"""
    levels = PriorityLevel.objects.filter(is_active=True).values(
        'id', 'name', 'display_name', 'description', 'color', 'numeric_value', 'sort_order'
    )
    return Response(list(levels))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_whatsapp_patterns(request):
    """Get all active WhatsApp patterns"""
    pattern_type = request.GET.get('type', None)
    patterns = WhatsAppPattern.objects.filter(is_active=True)
    
    if pattern_type:
        patterns = patterns.filter(pattern_type=pattern_type)
    
    patterns = patterns.values(
        'id', 'pattern_type', 'pattern_value', 'description', 'is_regex', 'sort_order'
    )
    return Response(list(patterns))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_variations(request):
    """Get all active product variations"""
    variations = ProductVariation.objects.filter(is_active=True).values(
        'id', 'original_name', 'normalized_name', 'description'
    )
    return Response(list(variations))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_company_aliases(request):
    """Get all active company aliases"""
    aliases = CompanyAlias.objects.filter(is_active=True).values(
        'id', 'alias', 'company_name', 'description'
    )
    return Response(list(aliases))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_configuration(request):
    """Get all configuration data in one call for efficiency"""
    return Response({
        'customer_segments': list(CustomerSegment.objects.filter(is_active=True).values(
            'id', 'name', 'description', 'default_markup', 'credit_limit_multiplier', 'payment_terms_days'
        )),
        'order_statuses': list(OrderStatus.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'color', 'is_final', 'sort_order'
        )),
        'adjustment_types': list(StockAdjustmentType.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'affects_cost', 'requires_reason'
        )),
        'departments': list(Department.objects.filter(is_active=True).values(
            'id', 'name', 'description'
        )),
        'units_of_measure': list(UnitOfMeasure.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'category', 'sort_order'
        )),
        'message_types': list(MessageType.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'color', 'sort_order'
        )),
        'user_types': list(UserType.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'permissions', 'sort_order'
        )),
        'supplier_types': list(SupplierType.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'sort_order'
        )),
        'invoice_statuses': list(InvoiceStatus.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'color', 'is_final', 'sort_order'
        )),
        'payment_methods': list(PaymentMethod.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'requires_reference', 'sort_order'
        )),
        'production_statuses': list(ProductionStatus.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'color', 'is_final', 'sort_order'
        )),
        'quality_grades': list(QualityGrade.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'color', 'sort_order'
        )),
        'priority_levels': list(PriorityLevel.objects.filter(is_active=True).values(
            'id', 'name', 'display_name', 'description', 'color', 'numeric_value', 'sort_order'
        )),
        'whatsapp_patterns': list(WhatsAppPattern.objects.filter(is_active=True).values(
            'id', 'pattern_type', 'pattern_value', 'description', 'is_regex', 'sort_order'
        )),
        'product_variations': list(ProductVariation.objects.filter(is_active=True).values(
            'id', 'original_name', 'normalized_name', 'description'
        )),
        'company_aliases': list(CompanyAlias.objects.filter(is_active=True).values(
            'id', 'alias', 'company_name', 'description'
        )),
        'business_config': {
            config.name: {
                'value': config.get_value(),
                'display_name': config.display_name,
                'description': config.description,
                'category': config.category,
                'type': config.value_type
            }
            for config in BusinessConfiguration.objects.filter(is_active=True)
        }
    })
