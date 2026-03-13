from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProfileViewSet,
    HardwareStoreViewSet,
    ProductViewSet,
    OrderViewSet,
    NotificationViewSet,
)
from .views import health_check

router = DefaultRouter()
router.register("profiles", ProfileViewSet, basename="profile")
router.register("hardware_stores", HardwareStoreViewSet, basename="hardwarestore")
router.register("products", ProductViewSet, basename="product")
router.register("orders", OrderViewSet, basename="order")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("", include(router.urls)),
]
