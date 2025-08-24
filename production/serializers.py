from rest_framework import serializers
from .models import ProductionReservation


class ProductionReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionReservation
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "started_at", "completed_at")


