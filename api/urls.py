from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfileViewSet, HardwareStoreViewSet, ProductViewSet, OrderViewSet

router = DefaultRouter()
router.register('profiles', ProfileViewSet, basename='profile')
router.register('hardware_stores', HardwareStoreViewSet, basename='hardwarestore')
router.register('products', ProductViewSet, basename='product')
router.register('orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]
