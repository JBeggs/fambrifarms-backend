from rest_framework import generics, viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
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