from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API endpoints
router = DefaultRouter()
router.register(r'suppliers', views.SupplierViewSet, basename='supplier')
router.register(r'sales-reps', views.SalesRepViewSet, basename='salesrep')

urlpatterns = [
    path('', include(router.urls)),
]
