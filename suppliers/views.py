from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import Supplier, SalesRep, SupplierProduct
from .serializers import SupplierSerializer, SalesRepSerializer, SupplierProductSerializer
from .performance_tracking import SupplierPerformanceTracker

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Supplier.objects.all()
        is_active = self.request.query_params.get('is_active')  # None means no filter
        supplier_type = self.request.query_params.get('supplier_type')  # None means no filter
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if supplier_type is not None:
            queryset = queryset.filter(supplier_type=supplier_type.lower())
            
        return queryset
    
    @action(detail=True, methods=['get'])
    def sales_reps(self, request, pk=None):
        """Get sales reps for a specific supplier"""
        supplier = self.get_object()
        sales_reps = supplier.sales_reps.filter(is_active=True)
        serializer = SalesRepSerializer(sales_reps, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get products for a specific supplier with pricing and availability"""
        supplier = self.get_object()
        supplier_products = supplier.supplier_products.select_related('product', 'product__department')
        
        # Filter by availability if requested
        is_available = request.query_params.get('is_available')
        if is_available is not None:
            supplier_products = supplier_products.filter(is_available=is_available.lower() == 'true')
        
        # Search by product name if requested
        search = request.query_params.get('search')
        if search:
            supplier_products = supplier_products.filter(
                Q(product__name__icontains=search) |
                Q(supplier_product_name__icontains=search)
            )
        
        serializer = SupplierProductSerializer(supplier_products, many=True)
        return Response(serializer.data)

class SalesRepViewSet(viewsets.ModelViewSet):
    queryset = SalesRep.objects.all()
    serializer_class = SalesRepSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = SalesRep.objects.all()
        supplier_id = self.request.query_params.get('supplier')  # None means no filter
        is_active = self.request.query_params.get('is_active')  # None means no filter
        
        if supplier_id is not None:
            queryset = queryset.filter(supplier_id=supplier_id)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset

class SupplierProductViewSet(viewsets.ModelViewSet):
    queryset = SupplierProduct.objects.all()
    serializer_class = SupplierProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = SupplierProduct.objects.select_related('supplier', 'product', 'product__department')
        
        # Filter by supplier
        supplier_id = self.request.query_params.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by product
        product_id = self.request.query_params.get('product')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by availability
        is_available = self.request.query_params.get('is_available')
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available.lower() == 'true')
        
        # Search by product name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(product__name__icontains=search) |
                Q(supplier_product_name__icontains=search)
            )
        
        return queryset.order_by('supplier__name', 'product__name')

# Supplier Performance Tracking Endpoints
@api_view(['GET'])
@permission_classes([AllowAny])
def get_supplier_performance(request, supplier_id):
    """
    Get comprehensive performance analysis for a specific supplier
    Query params: ?days_back=90
    """
    try:
        days_back = int(request.query_params.get('days_back', 90))
        supplier = get_object_or_404(Supplier, id=supplier_id)
        
        # Initialize performance tracker
        tracker = SupplierPerformanceTracker()
        
        # Get performance analysis
        performance = tracker.calculate_supplier_performance_score(supplier, days_back)
        
        return Response(performance, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to get supplier performance: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_supplier_rankings(request):
    """
    Get ranked list of all suppliers by performance
    Query params: ?days_back=90
    """
    try:
        days_back = int(request.query_params.get('days_back', 90))
        
        # Initialize performance tracker
        tracker = SupplierPerformanceTracker()
        
        # Get supplier rankings
        rankings = tracker.get_supplier_rankings(days_back)
        
        return Response({
            'success': True,
            'evaluation_period_days': days_back,
            'total_suppliers': len(rankings),
            'rankings': rankings
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to get supplier rankings: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_performance_dashboard(request):
    """
    Get comprehensive performance dashboard data
    """
    try:
        days_back = int(request.query_params.get('days_back', 90))
        
        # Initialize performance tracker
        tracker = SupplierPerformanceTracker()
        
        # Get all supplier rankings
        rankings = tracker.get_supplier_rankings(days_back)
        
        # Calculate dashboard metrics
        total_suppliers = len(rankings)
        platinum_suppliers = len([s for s in rankings if s['performance_tier'] == 'platinum'])
        gold_suppliers = len([s for s in rankings if s['performance_tier'] == 'gold'])
        needs_improvement = len([s for s in rankings if s['performance_tier'] == 'needs_improvement'])
        
        # Calculate average scores by tier
        tier_averages = {}
        for tier in ['platinum', 'gold', 'silver', 'bronze', 'needs_improvement']:
            tier_suppliers = [s for s in rankings if s['performance_tier'] == tier]
            if tier_suppliers:
                tier_averages[tier] = {
                    'count': len(tier_suppliers),
                    'average_score': sum(s['overall_score'] for s in tier_suppliers) / len(tier_suppliers)
                }
            else:
                tier_averages[tier] = {'count': 0, 'average_score': 0}
        
        # Top and bottom performers
        top_performers = rankings[:3] if rankings else []
        bottom_performers = rankings[-3:] if len(rankings) >= 3 else []
        
        # Fambri vs External performance
        fambri_suppliers = [s for s in rankings if s['supplier_type'] == 'internal']
        external_suppliers = [s for s in rankings if s['supplier_type'] == 'external']
        
        fambri_avg = sum(s['overall_score'] for s in fambri_suppliers) / len(fambri_suppliers) if fambri_suppliers else 0
        external_avg = sum(s['overall_score'] for s in external_suppliers) / len(external_suppliers) if external_suppliers else 0
        
        dashboard_data = {
            'success': True,
            'evaluation_period_days': days_back,
            'summary': {
                'total_suppliers': total_suppliers,
                'platinum_suppliers': platinum_suppliers,
                'gold_suppliers': gold_suppliers,
                'needs_improvement': needs_improvement,
                'overall_average_score': sum(s['overall_score'] for s in rankings) / total_suppliers if total_suppliers > 0 else 0
            },
            'tier_distribution': tier_averages,
            'performance_comparison': {
                'fambri_internal': {
                    'count': len(fambri_suppliers),
                    'average_score': round(fambri_avg, 2)
                },
                'external_suppliers': {
                    'count': len(external_suppliers),
                    'average_score': round(external_avg, 2)
                }
            },
            'top_performers': top_performers,
            'bottom_performers': bottom_performers,
            'all_suppliers': rankings
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to get performance dashboard: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
