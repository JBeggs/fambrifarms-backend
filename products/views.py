from rest_framework import generics, viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Product, Department, ProductAlert, Recipe
from .serializers import ProductSerializer, DepartmentSerializer

@api_view(['GET'])
def api_overview(request):
    """API overview showing available endpoints"""
    urls = {
        'products': '/api/products/products/',
        'departments': '/api/products/departments/',
        'product_alerts': '/api/products/alerts/',
    }
    return Response(urls)

class ProductListView(generics.ListCreateAPIView):
    """List all products or create a new product"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Product.objects.select_related('department').all()
        
        # Filter by needs_setup
        needs_setup = self.request.query_params.get('needs_setup')
        if needs_setup is not None:
            queryset = queryset.filter(needs_setup=needs_setup.lower() == 'true')
            
        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__name__icontains=department)
            
        return queryset.order_by('name')

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a product"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

class DepartmentListView(generics.ListCreateAPIView):
    """List all departments or create a new department"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]

@api_view(['GET'])
def product_alerts(request):
    """Get unresolved product alerts"""
    alerts = ProductAlert.objects.filter(is_resolved=False).select_related('product')
    
    alert_data = []
    for alert in alerts:
        alert_data.append({
            'id': alert.id,
            'product_id': alert.product.id,
            'product_name': alert.product.name,
            'alert_type': alert.alert_type,
            'message': alert.message,
            'created_at': alert.created_at,
            'created_by_order': alert.created_by_order,
        })
    
    return Response({
        'count': len(alert_data),
        'alerts': alert_data
    })

@api_view(['POST'])
def resolve_alert(request, alert_id):
    """Mark an alert as resolved"""
    alert = get_object_or_404(ProductAlert, id=alert_id)
    alert.is_resolved = True
    alert.resolved_by = request.user if request.user.is_authenticated else None
    alert.save()
    
    return Response({'message': 'Alert resolved successfully'})