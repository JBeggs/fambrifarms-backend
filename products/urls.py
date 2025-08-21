from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'products', views.ProductViewSet, basename='product')

# CMS ViewSets
router.register(r'company-info', views.CompanyInfoViewSet, basename='company-info')
router.register(r'business-hours', views.BusinessHoursViewSet, basename='business-hours')
router.register(r'team-members', views.TeamMemberViewSet, basename='team-members')
router.register(r'faqs', views.FAQViewSet, basename='faqs')
router.register(r'testimonials', views.TestimonialViewSet, basename='testimonials')

urlpatterns = [
    # API Overview
    path('', views.api_overview, name='api-overview'),
    
    # Include ViewSet URLs
    path('', include(router.urls)),
    
    # CMS endpoints
    path('company/', views.company_info, name='company-info'),
    path('page-content/<str:page>/', views.page_content, name='page-content'),
    
    # Legacy endpoints for backward compatibility
    path('products-list/', views.ProductListView.as_view(), name='product-list-legacy'),
    path('products-detail/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail-legacy'),
    path('departments-list/', views.DepartmentListView.as_view(), name='department-list-legacy'),
] 