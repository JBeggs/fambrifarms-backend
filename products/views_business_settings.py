"""
Business Settings API Views for Fambri Farms
Handles configurable business settings to replace hardcoded values
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
import logging

from .models_business_settings import BusinessSettings
from rest_framework import serializers

logger = logging.getLogger(__name__)

class BusinessSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSettings
        fields = [
            'id',
            # Procurement Buffer Settings
            'default_spoilage_rate',
            'default_cutting_waste_rate', 
            'default_quality_rejection_rate',
            'default_market_pack_size',
            'default_peak_season_multiplier',
            'department_buffer_settings',
            'enable_seasonal_adjustments',
            'auto_create_buffers',
            'buffer_calculation_method',
            # Other settings
            'default_minimum_level',
            'default_reorder_level',
            'default_maximum_level',
            'max_price_variance_percent',
            'require_price_approval_above',
            'allow_negative_inventory',
            'auto_create_purchase_orders',
            'updated_at',
            'updated_by'
        ]
        read_only_fields = ['id', 'updated_at', 'updated_by']

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_business_settings(request):
    """
    Get current business settings
    
    GET /api/products/business-settings/
    """
    try:
        settings = BusinessSettings.get_settings()
        serializer = BusinessSettingsSerializer(settings)
        
        return Response({
            'success': True,
            'settings': serializer.data
        })
        
    except Exception as e:
        logger.error(f"Error fetching business settings: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_business_settings(request):
    """
    Update business settings
    
    PUT /api/products/business-settings/
    Body: {
        "default_spoilage_rate": 0.15,
        "default_cutting_waste_rate": 0.10,
        "default_quality_rejection_rate": 0.05,
        "default_market_pack_size": 5.0,
        "default_peak_season_multiplier": 1.3,
        "department_buffer_settings": {
            "Vegetables": {
                "spoilage_rate": 0.15,
                "cutting_waste_rate": 0.12,
                "quality_rejection_rate": 0.08,
                "market_pack_size": 5.0,
                "market_pack_unit": "kg",
                "is_seasonal": true,
                "peak_season_months": [11, 12, 1, 2, 3],
                "peak_season_buffer_multiplier": 1.3
            }
        },
        "enable_seasonal_adjustments": true,
        "auto_create_buffers": true,
        "buffer_calculation_method": "additive"
    }
    """
    try:
        settings = BusinessSettings.get_settings()
        
        # Update settings with request data
        serializer = BusinessSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            with transaction.atomic():
                # Set the user who updated the settings
                serializer.save(updated_by=request.user)
                
                return Response({
                    'success': True,
                    'message': 'Business settings updated successfully',
                    'settings': serializer.data
                })
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error updating business settings: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_department_buffer_settings(request):
    """
    Get department-specific buffer settings
    
    GET /api/products/business-settings/departments/
    """
    try:
        settings = BusinessSettings.get_settings()
        
        return Response({
            'success': True,
            'department_settings': settings.department_buffer_settings,
            'global_defaults': {
                'spoilage_rate': float(settings.default_spoilage_rate),
                'cutting_waste_rate': float(settings.default_cutting_waste_rate),
                'quality_rejection_rate': float(settings.default_quality_rejection_rate),
                'market_pack_size': float(settings.default_market_pack_size),
                'peak_season_multiplier': float(settings.default_peak_season_multiplier)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching department buffer settings: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_department_buffer_settings(request, department_name):
    """
    Update buffer settings for a specific department
    
    PUT /api/products/business-settings/departments/{department_name}/
    Body: {
        "spoilage_rate": 0.15,
        "cutting_waste_rate": 0.12,
        "quality_rejection_rate": 0.08,
        "market_pack_size": 5.0,
        "market_pack_unit": "kg",
        "is_seasonal": true,
        "peak_season_months": [11, 12, 1, 2, 3],
        "peak_season_buffer_multiplier": 1.3
    }
    """
    try:
        settings = BusinessSettings.get_settings()
        
        # Get current department settings
        dept_settings = settings.department_buffer_settings.copy()
        
        # Update the specific department
        dept_settings[department_name] = request.data
        
        # Save back to settings
        settings.department_buffer_settings = dept_settings
        settings.updated_by = request.user
        settings.save()
        
        return Response({
            'success': True,
            'message': f'Updated buffer settings for {department_name}',
            'department_settings': dept_settings[department_name]
        })
        
    except Exception as e:
        logger.error(f"Error updating department buffer settings: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_to_defaults(request):
    """
    Reset business settings to default values
    
    POST /api/products/business-settings/reset/
    """
    try:
        with transaction.atomic():
            # Delete existing settings to trigger recreation with defaults
            BusinessSettings.objects.all().delete()
            
            # Get new settings with defaults
            settings = BusinessSettings.get_settings()
            settings.updated_by = request.user
            settings.save()
            
            serializer = BusinessSettingsSerializer(settings)
            
            return Response({
                'success': True,
                'message': 'Business settings reset to defaults',
                'settings': serializer.data
            })
            
    except Exception as e:
        logger.error(f"Error resetting business settings: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
