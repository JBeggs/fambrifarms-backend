from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from .models import Invoice
from .serializers import InvoiceSerializer


class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type == 'admin':
            return Invoice.objects.all().order_by('-created_at')
        return Invoice.objects.filter(restaurant=self.request.user).order_by('-created_at')


class InvoiceDetailView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.user_type == 'admin':
            return Invoice.objects.all()
        return Invoice.objects.filter(restaurant=self.request.user)

