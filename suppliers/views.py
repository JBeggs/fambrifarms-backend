from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Avg

from .models import Supplier, SupplierProduct
from .serializers import (
    SupplierListSerializer, SupplierDetailSerializer,
    SupplierProductListSerializer, SupplierProductDetailSerializer,
    SupplierStockUpdateSerializer
)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SupplierListSerializer
        return SupplierDetailSerializer
    
    def get_queryset(self):
        queryset = Supplier.objects.all()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search by name, contact name, or email
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(contact_name__icontains=search) |
                Q(contact_email__icontains=search)
            )
        
        # Filter by city
        city = self.request.query_params.get('city', None)
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        return queryset.order_by('name')
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products supplied by this supplier"""
        supplier = self.get_object()
        products = supplier.products.all().order_by('product__name')
        serializer = SupplierProductListSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def available_products(self, request, pk=None):
        """Get available products from this supplier"""
        supplier = self.get_object()
        products = supplier.products.filter(
            is_available=True,
            stock_quantity__gt=0
        ).order_by('product__name')
        serializer = SupplierProductListSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def performance_summary(self, request):
        """Get supplier performance summary"""
        suppliers = self.get_queryset().annotate(
            product_count=Count('products'),
            avg_price=Avg('products__supplier_price'),
            available_products=Count('products', filter=Q(products__is_available=True))
        )
        
        summary = []
        for supplier in suppliers:
            summary.append({
                'supplier_id': supplier.id,
                'supplier_name': supplier.name,
                'contact_name': supplier.contact_name,
                'city': supplier.city,
                'total_products': supplier.product_count,
                'available_products': supplier.available_products,
                'average_price': supplier.avg_price,
                'is_active': supplier.is_active
            })
        
        return Response(summary)


class SupplierProductViewSet(viewsets.ModelViewSet):
    queryset = SupplierProduct.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SupplierProductListSerializer
        return SupplierProductDetailSerializer
    
    def get_queryset(self):
        queryset = SupplierProduct.objects.select_related(
            'supplier', 'product__department'
        ).all()
        
        # Filter by supplier
        supplier_id = self.request.query_params.get('supplier', None)
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Filter by product
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by department
        department_id = self.request.query_params.get('department', None)
        if department_id:
            queryset = queryset.filter(product__department_id=department_id)
        
        # Filter by availability
        is_available = self.request.query_params.get('is_available', None)
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available.lower() == 'true')
        
        # Filter by stock availability
        has_stock = self.request.query_params.get('has_stock', None)
        if has_stock is not None:
            if has_stock.lower() == 'true':
                queryset = queryset.filter(stock_quantity__gt=0)
            else:
                queryset = queryset.filter(stock_quantity=0)
        
        # Price range filters
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            queryset = queryset.filter(supplier_price__gte=min_price)
        if max_price:
            queryset = queryset.filter(supplier_price__lte=max_price)
        
        return queryset.order_by('supplier__name', 'product__name')
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get supplier products with low or no stock"""
        low_stock_threshold = int(request.query_params.get('threshold', 10))
        
        queryset = self.get_queryset().filter(
            stock_quantity__lte=low_stock_threshold,
            is_available=True
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def price_comparison(self, request):
        """Compare prices across suppliers for the same products"""
        product_id = request.query_params.get('product_id')
        
        if not product_id:
            return Response(
                {'error': 'product_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        supplier_products = self.get_queryset().filter(
            product_id=product_id,
            is_available=True
        ).order_by('supplier_price')
        
        serializer = self.get_serializer(supplier_products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_stock(self, request, pk=None):
        """Update supplier stock quantity"""
        supplier_product = self.get_object()
        serializer = SupplierStockUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            old_quantity = supplier_product.stock_quantity
            new_quantity = serializer.validated_data['new_stock_quantity']
            notes = serializer.validated_data.get('notes', '')
            
            supplier_product.stock_quantity = new_quantity
            supplier_product.save()
            
            # Create a stock movement record for audit trail
            from inventory.models import StockMovement
            StockMovement.objects.create(
                movement_type='finished_adjust',
                reference_number=f'SUP-{supplier_product.supplier.id}-{pk}',
                product=supplier_product.product,
                quantity=new_quantity - old_quantity,
                unit_cost=supplier_product.supplier_price,
                total_value=(new_quantity - old_quantity) * supplier_product.supplier_price,
                user=request.user,
                notes=f'Supplier stock update: {old_quantity} → {new_quantity}. {notes}'.strip()
            )
            
            return Response(
                self.get_serializer(supplier_product).data,
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def supplier_summary(request):
    """Get overall supplier summary statistics"""
    total_suppliers = Supplier.objects.count()
    active_suppliers = Supplier.objects.filter(is_active=True).count()
    total_products = SupplierProduct.objects.count()
    available_products = SupplierProduct.objects.filter(
        is_available=True,
        stock_quantity__gt=0
    ).count()
    
    # Get suppliers by city
    suppliers_by_city = {}
    for supplier in Supplier.objects.filter(is_active=True):
        city = supplier.city or 'Unknown'
        if city not in suppliers_by_city:
            suppliers_by_city[city] = 0
        suppliers_by_city[city] += 1
    
    summary = {
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers,
        'total_products': total_products,
        'available_products': available_products,
        'out_of_stock_products': total_products - available_products,
        'suppliers_by_city': suppliers_by_city
    }
    
    return Response(summary)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def best_prices(request):
    """Get best prices for each product across all suppliers"""
    from products.models import Product
    
    products = Product.objects.filter(is_active=True)
    best_prices = []
    
    for product in products:
        supplier_products = SupplierProduct.objects.filter(
            product=product,
            is_available=True,
            stock_quantity__gt=0
        ).order_by('supplier_price')
        
        if supplier_products.exists():
            cheapest = supplier_products.first()
            most_expensive = supplier_products.last()
            
            best_prices.append({
                'product_id': product.id,
                'product_name': product.name,
                'department': product.department.name,
                'cheapest_supplier': cheapest.supplier.name,
                'cheapest_price': cheapest.supplier_price,
                'most_expensive_supplier': most_expensive.supplier.name,
                'most_expensive_price': most_expensive.supplier_price,
                'price_difference': most_expensive.supplier_price - cheapest.supplier_price,
                'suppliers_count': supplier_products.count()
            })
    
    # Sort by price difference (biggest savings opportunities first)
    best_prices.sort(key=lambda x: x['price_difference'], reverse=True)
    
    return Response(best_prices)
