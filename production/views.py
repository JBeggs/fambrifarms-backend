from rest_framework import viewsets, permissions
from .models import ProductionReservation
from .serializers import ProductionReservationSerializer


class ProductionReservationViewSet(viewsets.ModelViewSet):
    queryset = ProductionReservation.objects.all().order_by("-created_at")
    serializer_class = ProductionReservationSerializer
    permission_classes = [permissions.IsAuthenticated]


