from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductionReservationViewSet


router = DefaultRouter()
router.register(r"reservations", ProductionReservationViewSet, basename="production-reservation")

urlpatterns = [
    path("", include(router.urls)),
]


