from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# For future API endpoints
router = DefaultRouter()
# router.register(r'invoices', views.InvoiceViewSet)
# router.register(r'payments', views.PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # Add specific endpoints here as needed
]
