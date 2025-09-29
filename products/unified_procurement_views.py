"""
Unified Procurement API Views
Integrates market recommendations, supplier optimization, and automated workflows
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
import logging

from .unified_procurement_service import UnifiedProcurementService
from .models import Product, MarketProcurementRecommendation
from orders.models import Order
from suppliers.models import Supplier
from suppliers.performance_tracking import SupplierPerformanceTracker

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def unified_procurement_analysis(request):
    """
    Unified procurement analysis that combines:
    1. Market recommendations
    2. Supplier optimization
    3. Performance metrics
    4. Cost analysis
    """
    try:
        # Get request parameters
        analysis_type = request.data.get('analysis_type', 'comprehensive')  # comprehensive, market, supplier, order
        order_id = request.data.get('order_id')
        product_ids = request.data.get('product_ids', [])
        for_date = request.data.get('for_date')
        use_historical_dates = request.data.get('use_historical_dates', True)
        
        # Initialize services
        procurement_service = UnifiedProcurementService()
        performance_tracker = SupplierPerformanceTracker()
        
        result = {
            'success': True,
            'analysis_type': analysis_type,
            'timestamp': timezone.now().isoformat(),
            'data': {}
        }
        
        if analysis_type == 'comprehensive' or analysis_type == 'market':
            # Generate market recommendation with supplier integration
            if for_date:
                for_date_obj = datetime.strptime(for_date, '%Y-%m-%d').date()
            else:
                for_date_obj = None
                
            recommendation = procurement_service.generate_market_recommendation(
                for_date=for_date_obj,
                use_historical_dates=use_historical_dates
            )
            
            result['data']['market_recommendation'] = {
                'id': recommendation.id,
                'for_date': recommendation.for_date.isoformat(),
                'total_cost': float(recommendation.total_estimated_cost),
                'items_count': recommendation.items_count,
                'reasoning': recommendation.reasoning,
                'items': []
            }
            
            # Add detailed item information with supplier integration
            for item in recommendation.items.all():
                item_data = {
                    'product_id': item.product.id,
                    'product_name': item.product.name,
                    'needed_quantity': float(item.needed_quantity),
                    'recommended_quantity': float(item.recommended_quantity),
                    'estimated_unit_price': float(item.estimated_unit_price),
                    'estimated_total_cost': float(item.estimated_total_cost),
                    'priority': item.priority,
                    'reasoning': item.reasoning,
                    'procurement_method': item.procurement_method,
                    'is_fambri_available': item.is_fambri_available,
                    'supplier_info': None
                }
                
                # Add supplier information if available
                if item.preferred_supplier:
                    item_data['supplier_info'] = {
                        'supplier_id': item.preferred_supplier.id,
                        'supplier_name': item.preferred_supplier.name,
                        'supplier_type': 'internal' if 'Fambri' in item.preferred_supplier.name else 'external',
                        'unit_price': float(item.supplier_unit_price) if item.supplier_unit_price else None,
                        'quality_rating': float(item.supplier_quality_rating) if item.supplier_quality_rating else None,
                        'lead_time_days': item.supplier_lead_time_days
                    }
                
                result['data']['market_recommendation']['items'].append(item_data)
        
        if analysis_type == 'comprehensive' or analysis_type == 'supplier':
            # Add supplier performance analysis
            suppliers = Supplier.objects.filter(is_active=True)
            supplier_analysis = []
            
            for supplier in suppliers:
                performance = performance_tracker.calculate_supplier_performance_score(supplier, 90)
                supplier_analysis.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'supplier_type': 'internal' if 'Fambri' in supplier.name else 'external',
                    'performance_score': performance.get('overall_score', 0),
                    'performance_tier': performance.get('performance_tier', 'unrated'),
                    'available_products': supplier.supplier_products.filter(is_available=True).count()
                })
            
            # Sort by performance score
            supplier_analysis.sort(key=lambda x: x['performance_score'], reverse=True)
            result['data']['supplier_analysis'] = supplier_analysis
        
        if analysis_type == 'comprehensive' or analysis_type == 'order':
            # Add order-specific analysis if order_id provided
            if order_id:
                order = get_object_or_404(Order, id=order_id)
                order_analysis = procurement_service.create_procurement_from_order(order)
                result['data']['order_analysis'] = order_analysis
        
        # Add unified metrics
        if analysis_type == 'comprehensive':
            result['data']['unified_metrics'] = _calculate_unified_metrics(
                result['data'], procurement_service
            )
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in unified procurement analysis: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def unified_procurement_dashboard(request):
    """
    Unified procurement dashboard with integrated metrics
    """
    try:
        # Initialize services
        procurement_service = UnifiedProcurementService()
        performance_tracker = SupplierPerformanceTracker()
        
        # Get recent recommendations
        recent_recommendations = MarketProcurementRecommendation.objects.filter(
            status='pending'
        ).order_by('-created_at')[:5]
        
        # Calculate dashboard metrics
        dashboard_data = {
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'summary': {
                'pending_recommendations': recent_recommendations.count(),
                'total_estimated_cost': sum(r.total_estimated_cost for r in recent_recommendations),
                'active_suppliers': Supplier.objects.filter(is_active=True).count(),
                'fambri_utilization': 0.0  # Will be calculated below
            },
            'recent_recommendations': [],
            'supplier_performance_summary': {},
            'procurement_methods_breakdown': {
                'fambri': 0,
                'supplier': 0,
                'market': 0,
                'mixed': 0
            }
        }
        
        # Process recent recommendations
        fambri_items = 0
        total_items = 0
        
        for recommendation in recent_recommendations:
            items_data = []
            
            for item in recommendation.items.all():
                total_items += 1
                if item.is_fambri_available:
                    fambri_items += 1
                
                # Count procurement methods
                method = item.procurement_method
                if method in dashboard_data['procurement_methods_breakdown']:
                    dashboard_data['procurement_methods_breakdown'][method] += 1
                
                items_data.append({
                    'product_name': item.product.name,
                    'recommended_quantity': float(item.recommended_quantity),
                    'estimated_cost': float(item.estimated_total_cost),
                    'priority': item.priority,
                    'procurement_method': item.procurement_method,
                    'is_fambri_available': item.is_fambri_available
                })
            
            dashboard_data['recent_recommendations'].append({
                'id': recommendation.id,
                'for_date': recommendation.for_date.isoformat(),
                'total_cost': float(recommendation.total_estimated_cost),
                'items_count': recommendation.items_count,
                'status': recommendation.status,
                'items': items_data
            })
        
        # Calculate Fambri utilization
        if total_items > 0:
            dashboard_data['summary']['fambri_utilization'] = round((fambri_items / total_items) * 100, 2)
        
        # Add supplier performance summary
        supplier_rankings = performance_tracker.get_supplier_rankings(30)
        dashboard_data['supplier_performance_summary'] = {
            'total_suppliers': len(supplier_rankings),
            'top_performer': supplier_rankings[0] if supplier_rankings else None,
            'average_score': sum(s['overall_score'] for s in supplier_rankings) / len(supplier_rankings) if supplier_rankings else 0,
            'fambri_score': next((s['overall_score'] for s in supplier_rankings if s['supplier_type'] == 'internal'), 0)
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in unified procurement dashboard: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def product_procurement_options(request):
    """
    Get all procurement options for specific products
    """
    try:
        product_ids = request.data.get('product_ids', [])
        quantities = request.data.get('quantities', {})  # {product_id: quantity}
        
        if not product_ids:
            return Response({
                'success': False,
                'error': 'product_ids is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        procurement_service = UnifiedProcurementService()
        performance_tracker = SupplierPerformanceTracker()
        
        results = []
        
        for product_id in product_ids:
            product = get_object_or_404(Product, id=product_id)
            quantity = Decimal(str(quantities.get(str(product_id), '1')))
            
            # Get best supplier option
            best_option = procurement_service.get_best_supplier_for_product(product, quantity)
            
            # Get supplier split options
            split_options = procurement_service.calculate_optimal_supplier_split(product, quantity)
            
            # Get supplier performance if available
            supplier_performance = None
            if best_option and best_option['supplier']:
                supplier_performance = performance_tracker.calculate_supplier_performance_score(
                    best_option['supplier'], 30
                )
            
            product_result = {
                'product_id': product.id,
                'product_name': product.name,
                'quantity_requested': float(quantity),
                'best_option': {
                    'supplier_name': best_option['supplier'].name if best_option else 'Market',
                    'unit_price': float(best_option['unit_price']) if best_option else 0,
                    'total_cost': float(best_option['total_cost']) if best_option else 0,
                    'can_fulfill': best_option['can_fulfill_full_order'] if best_option else False,
                    'is_fambri': best_option.get('is_fambri', False) if best_option else False,
                    'quality_rating': float(best_option['quality_rating']) if best_option else 0,
                    'lead_time_days': best_option['lead_time_days'] if best_option else 1
                },
                'split_options': split_options,
                'supplier_performance': {
                    'overall_score': supplier_performance.get('overall_score', 0) if supplier_performance else 0,
                    'performance_tier': supplier_performance.get('performance_tier', 'unrated') if supplier_performance else 'unrated'
                } if supplier_performance else None
            }
            
            results.append(product_result)
        
        return Response({
            'success': True,
            'products': results,
            'summary': {
                'total_products': len(results),
                'fambri_available': len([r for r in results if r['best_option']['is_fambri']]),
                'total_estimated_cost': sum(r['best_option']['total_cost'] for r in results)
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in product procurement options: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def _calculate_unified_metrics(data, procurement_service):
    """Calculate unified metrics across all procurement methods"""
    metrics = {
        'total_suppliers_available': 0,
        'fambri_utilization_percentage': 0.0,
        'average_supplier_performance': 0.0,
        'cost_optimization_potential': 0.0,
        'procurement_method_distribution': {
            'fambri': 0,
            'supplier': 0,
            'market': 0,
            'mixed': 0
        }
    }
    
    # Calculate from available data
    if 'market_recommendation' in data:
        items = data['market_recommendation']['items']
        total_items = len(items)
        fambri_items = len([item for item in items if item['is_fambri_available']])
        
        if total_items > 0:
            metrics['fambri_utilization_percentage'] = round((fambri_items / total_items) * 100, 2)
        
        # Count procurement methods
        for item in items:
            method = item['procurement_method']
            if method in metrics['procurement_method_distribution']:
                metrics['procurement_method_distribution'][method] += 1
    
    if 'supplier_analysis' in data:
        suppliers = data['supplier_analysis']
        metrics['total_suppliers_available'] = len(suppliers)
        
        if suppliers:
            metrics['average_supplier_performance'] = round(
                sum(s['performance_score'] for s in suppliers) / len(suppliers), 2
            )
    
    return metrics
