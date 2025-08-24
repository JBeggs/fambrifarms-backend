from django.urls import path
from . import views

urlpatterns = [
    path('', views.InvoiceListView.as_view(), name='invoice_list'),
    path('<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
]