from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Supplier, SalesRep, SupplierProduct
from .serializers import SupplierSerializer, SalesRepSerializer, SupplierProductSerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Supplier.objects.all()
        is_active = self.request.query_params.get('is_active')  # None means no filter
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset
    
    @action(detail=True, methods=['get'])
    def sales_reps(self, request, pk=None):
        """Get sales reps for a specific supplier"""
        supplier = self.get_object()
        sales_reps = supplier.sales_reps.filter(is_active=True)
        serializer = SalesRepSerializer(sales_reps, many=True)
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
