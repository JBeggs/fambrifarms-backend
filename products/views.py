from rest_framework import generics, viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.db import transaction
from .models import Product, Department, ProductAlert, Recipe
from .models_business_settings import BusinessSettings
from .serializers import ProductSerializer, DepartmentSerializer
from .serializers_business_settings import AppConfigSerializer
from .services import ProcurementIntelligenceService
from .unified_procurement_service import UnifiedProcurementService

User = get_user_model()

@api_view(['GET'])
def api_overview(request):
    """API overview showing available endpoints"""
    urls = {
        'products': '/api/products/products/',
        'departments': '/api/products/departments/',
        'product_alerts': '/api/products/alerts/',
        'app_config': '/api/products/app-config/',
    }
    return Response(urls)


@api_view(['GET'])
def app_config(request):
    """
    Get app configuration settings for Flutter app
    Single endpoint that provides all necessary configuration
    """
    try:
        settings = BusinessSettings.get_settings()
        serializer = AppConfigSerializer(settings)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': f'Failed to load app configuration: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ProductListView(generics.ListCreateAPIView):
    """List all products or create a new product"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    
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
    
    def update(self, request, *args, **kwargs):
        """Enhanced update with better error handling"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if not serializer.is_valid():
                # Log validation errors for debugging
                print(f"[PRODUCT_UPDATE] Validation errors: {serializer.errors}")
                print(f"[PRODUCT_UPDATE] Request data: {request.data}")
                return Response({
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            self.perform_update(serializer)
            
            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}
                
            return Response(serializer.data)
            
        except Exception as e:
            print(f"[PRODUCT_UPDATE] Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Internal server error',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

@api_view(['GET'])
def get_customer_price(request, product_id):
    """Get customer-specific price for a product"""
    try:
        product = get_object_or_404(Product, id=product_id)
        customer_id = request.GET.get('customer_id')
        
        if not customer_id:
            return Response({
                'error': 'customer_id parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            customer = User.objects.get(id=customer_id)
        except User.DoesNotExist:
            return Response({
                'error': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get customer-specific price using the product method
        customer_price = product.get_customer_price(customer)
        
        # Get pricing context for debugging
        from whatsapp.services import determine_customer_segment, get_customer_specific_price
        customer_segment = determine_customer_segment(customer)
        
        return Response({
            'product_id': product.id,
            'product_name': product.name,
            'base_price': float(product.price),
            'customer_price': float(customer_price),
            'customer_id': customer.id,
            'customer_segment': customer_segment,
            'price_difference': float(customer_price - product.price),
            'has_custom_pricing': customer_price != product.price,
        })
        
    except Exception as e:
        return Response({
            'error': f'Failed to get customer price: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Supplier Optimization Endpoints
@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_supplier_split(request):
    """
    Calculate optimal supplier split for a single product
    POST data: {'product_id': int, 'quantity': float}
    """
    try:
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        
        if not product_id or not quantity:
            return Response({
                'error': 'product_id and quantity are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product = get_object_or_404(Product, id=product_id)
        quantity_decimal = Decimal(str(quantity))
        
        # Initialize unified procurement service
        procurement_service = UnifiedProcurementService()
        
        # Calculate optimal split using unified logic
        result = procurement_service.calculate_optimal_supplier_split(product, quantity_decimal)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to calculate supplier split: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def calculate_order_optimization(request):
    """
    Calculate optimal supplier split for an entire order
    POST data: {'order_items': [{'product_id': int, 'quantity': float}, ...]}
    """
    try:
        order_items = request.data.get('order_items', [])
        
        if not order_items:
            return Response({
                'error': 'order_items array is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate order items format
        for item in order_items:
            if 'product_id' not in item or 'quantity' not in item:
                return Response({
                    'error': 'Each order item must have product_id and quantity'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize procurement service
        procurement_service = ProcurementIntelligenceService()
        
        # Calculate order optimization
        result = procurement_service.calculate_order_supplier_optimization(order_items)
        
        return Response(result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to calculate order optimization: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_supplier_recommendations(request, product_id):
    """
    Get supplier recommendations for a specific product
    Query params: ?quantity=float
    """
    try:
        quantity = request.query_params.get('quantity', '1')
        quantity_decimal = Decimal(str(quantity))
        
        product = get_object_or_404(Product, id=product_id)
        
        # Initialize unified procurement service
        procurement_service = UnifiedProcurementService()
        
        # Get supplier recommendations using unified logic
        supplier_option = procurement_service.get_best_supplier_for_product(product, quantity_decimal)
        
        # Convert to expected format
        if supplier_option:
            recommendations = [{
                'supplier_id': supplier_option['supplier'].id,
                'supplier_name': supplier_option['supplier'].name,
                'supplier_type': 'internal' if supplier_option['is_fambri'] else 'external',
                'unit_price': float(supplier_option['unit_price']),
                'available_quantity': float(supplier_option['available_quantity']),
                'can_fulfill_full_order': supplier_option['can_fulfill_full_order'],
                'total_cost': float(supplier_option['total_cost']),
                'lead_time_days': supplier_option['lead_time_days'],
                'quality_rating': float(supplier_option['quality_rating']),
                'priority': 1 if supplier_option['is_fambri'] else 2
            }]
        else:
            recommendations = []
        
        return Response({
            'product_id': product_id,
            'product_name': product.name,
            'quantity_requested': float(quantity_decimal),
            'suppliers': recommendations
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Failed to get supplier recommendations: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def quick_create_product(request):
    """
    Quick create product for missing items during order processing
    POST data: {'name': str, 'unit': str, 'price': float, 'department_name': str (optional)}
    """
    try:
        name = request.data.get('name', '').strip()
        unit = request.data.get('unit', '').strip()
        price = request.data.get('price')
        department_name = request.data.get('department_name', 'Vegetables').strip()
        
        # Validation
        if not name:
            return Response({
                'error': 'Product name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if not unit:
            return Response({
                'error': 'Unit is required'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if price is None:
            return Response({
                'error': 'Price is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate unit is in allowed choices
        from settings.models import UnitOfMeasure
        valid_units = list(UnitOfMeasure.objects.filter(is_active=True).values_list('name', flat=True))
        if unit not in valid_units:
            return Response({
                'error': f'Invalid unit. Must be one of: {", ".join(valid_units)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            price_decimal = Decimal(str(price))
            if price_decimal < 0:
                return Response({
                    'error': 'Price must be positive'
                }, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid price format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if product with same name and unit already exists
        existing_product = Product.objects.filter(name__iexact=name, unit=unit).first()
        if existing_product:
            return Response({
                'error': f'Product "{name}" with unit "{unit}" already exists',
                'existing_product': ProductSerializer(existing_product).data
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create department
        department, created = Department.objects.get_or_create(
            name=department_name,
            defaults={'description': f'Auto-created for {name}'}
        )
        
        # Create product
        with transaction.atomic():
            product = Product.objects.create(
                name=name,
                unit=unit,
                price=price_decimal,
                department=department,
                stock_level=Decimal('0.00'),
                minimum_stock=Decimal('5.00'),
                is_active=True,
                needs_setup=False,  # Since we're providing all required info
                description=f'Quick-created product for order processing'
            )
        
        return Response({
            'success': True,
            'message': f'Product "{name}" created successfully',
            'product': ProductSerializer(product).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': f'Failed to create product: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)