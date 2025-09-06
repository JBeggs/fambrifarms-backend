from rest_framework import generics, viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import (
    Product, Department, CompanyInfo, PageContent, BusinessHours, 
    TeamMember, FAQ, Testimonial
)
from .serializers import (
    ProductSerializer, DepartmentSerializer, CompanyInfoSerializer,
    PageContentSerializer, BusinessHoursSerializer, TeamMemberSerializer,
    FAQSerializer, TestimonialSerializer
)

@api_view(['GET'])
def api_overview(request):
    """API overview showing available endpoints"""
    urls = {
        'Products': '/products/',
        'Product Detail': '/products/<int:id>/',
        'Departments': '/departments/',
        'Department Detail': '/departments/<int:id>/',
    }
    return Response(urls)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Department.objects.all()
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Product.objects.all()
        department = self.request.query_params.get('department', None)
        is_active = self.request.query_params.get('is_active', None)
        
        if department is not None:
            queryset = queryset.filter(department=department)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create product and optionally create FinishedInventory record"""
        try:
            # Create the product
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            product = serializer.save()
            
            # Create FinishedInventory if requested
            create_inventory = request.data.get('create_inventory', False)
            if create_inventory:
                from inventory.models import FinishedInventory
                initial_stock = request.data.get('initial_stock', 0)
                minimum_level = request.data.get('minimum_level', 5)
                reorder_level = request.data.get('reorder_level', 10)
                
                # Use get_or_create to avoid unique constraint errors
                inventory, created = FinishedInventory.objects.get_or_create(
                    product=product,
                    defaults={
                        'available_quantity': initial_stock,
                        'reserved_quantity': 0,
                        'minimum_level': minimum_level,
                        'reorder_level': reorder_level,
                        'average_cost': product.price
                    }
                )
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create product: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Update product and optionally create FinishedInventory record"""
        try:
            # Update the product
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            product = serializer.save()
            
            # Create FinishedInventory if requested and doesn't exist
            create_inventory = request.data.get('create_inventory', False)
            if create_inventory:
                from inventory.models import FinishedInventory
                
                # Check if inventory already exists
                if not hasattr(product, 'inventory'):
                    initial_stock = request.data.get('initial_stock', 0)
                    minimum_level = request.data.get('minimum_level', 5)
                    reorder_level = request.data.get('reorder_level', 10)
                    
                    FinishedInventory.objects.create(
                        product=product,
                        available_quantity=initial_stock,
                        reserved_quantity=0,
                        minimum_level=minimum_level,
                        reorder_level=reorder_level,
                        average_cost=product.price
                    )
            
            # Add stock to existing inventory if requested
            add_stock = request.data.get('add_stock')
            if add_stock is not None and add_stock > 0:
                from inventory.models import FinishedInventory
                
                # Get or create inventory record
                inventory, created = FinishedInventory.objects.get_or_create(
                    product=product,
                    defaults={
                        'available_quantity': 0,
                        'reserved_quantity': 0,
                        'minimum_level': 5,
                        'reorder_level': 10,
                        'average_cost': product.price
                    }
                )
                
                # Add the stock
                inventory.available_quantity += add_stock
                inventory.save()
                
                # Log the adjustment (in a full system, you'd have proper audit logging)
                adjustment_type = request.data.get('adjustment_type', 'manual_add')
                print(f"Stock adjustment: Added {add_stock} {product.unit} to {product.name} ({adjustment_type})")
            
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to update product: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Keep legacy views for backward compatibility
class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

class DepartmentListView(generics.ListAPIView):
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]


# CMS Views
class CompanyInfoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CompanyInfo.objects.filter(is_active=True)
    serializer_class = CompanyInfoSerializer
    permission_classes = [AllowAny]

@api_view(['GET'])
def company_info(request):
    """Get active company information"""
    try:
        company = CompanyInfo.objects.filter(is_active=True).first()
        if company:
            serializer = CompanyInfoSerializer(company)
            return Response(serializer.data)
        return Response({'error': 'Company information not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def page_content(request, page):
    """Get content for a specific page"""
    try:
        content = PageContent.objects.filter(page=page, is_active=True).first()
        if content:
            serializer = PageContentSerializer(content)
            return Response(serializer.data)
        return Response({'error': f'Content for page "{page}" not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

class BusinessHoursViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BusinessHours.objects.all()
    serializer_class = BusinessHoursSerializer
    permission_classes = [AllowAny]

class TeamMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TeamMember.objects.filter(is_active=True)
    serializer_class = TeamMemberSerializer
    permission_classes = [AllowAny]

class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.filter(is_active=True)
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]

class TestimonialViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Testimonial.objects.filter(is_active=True)
    serializer_class = TestimonialSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Testimonial.objects.filter(is_active=True)
        is_featured = self.request.query_params.get('is_featured', None)
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == 'true')
        return queryset 