from django.shortcuts import get_object_or_404
from django.db import transaction, connection
from django.core.cache import cache
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    AllowAny,
)
from core.models import (
    Profile,
    HardwareStore,
    Product,
    CommissionSetting,
    Order,
    OrderItem,
    Notification,
)
from .serializers import (
    ProfileSerializer,
    HardwareStoreSerializer,
    ProductSerializer,
    OrderSerializer,
    NotificationSerializer,
)
import math


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    health = {
        "status": "healthy",
        "database": "unknown",
        "cache": "unknown",
    }

    try:
        connection.ensure_connection()
        health["database"] = "connected"
    except Exception as e:
        health["status"] = "unhealthy"
        health["database"] = f"error: {str(e)}"

    try:
        cache.set("health_check", "ok", 10)
        if cache.get("health_check") == "ok":
            health["cache"] = "connected"
    except Exception as e:
        health["cache"] = f"unavailable: {str(e)}"

    status_code = 200 if health["status"] == "healthy" else 503
    return Response(health, status=status_code)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class HardwareStoreViewSet(viewsets.ModelViewSet):
    queryset = HardwareStore.objects.filter(active=True)
    serializer_class = HardwareStoreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")
        radius = float(request.query_params.get("radius", 10))

        if not lat or not lng:
            return Response(
                {"detail": "lat and lng are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat = float(lat)
            lng = float(lng)
        except ValueError:
            return Response(
                {"detail": "lat and lng must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stores = HardwareStore.objects.filter(
            active=True, latitude__isnull=False, longitude__isnull=False
        )
        nearby_stores = []
        for store in stores:
            distance = haversine_distance(lat, lng, store.latitude, store.longitude)
            if distance <= radius:
                store_data = HardwareStoreSerializer(store).data
                store_data["distance_km"] = round(distance, 2)
                nearby_stores.append(store_data)

        nearby_stores.sort(key=lambda x: x["distance_km"])
        return Response(nearby_stores)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        category = self.request.query_params.get("category")
        qs = super().get_queryset()
        if category:
            qs = qs.filter(category=category)
        return qs

    def perform_create(self, serializer):
        profile = self.request.user.profile
        if profile.role == "hardware":
            store = HardwareStore.objects.filter(owner=profile).first()
            if store:
                serializer.save(store=store)
            else:
                serializer.save()
        else:
            serializer.save()

    def perform_destroy(self, instance):
        profile = self.request.user.profile
        if profile.role == "hardware" and instance.store.owner != profile:
            return
        instance.delete()


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def place_order(self, request):
        """
        Expected payload:
        {
            "fundi_id": "uuid",
            "delivery_area": "Arusha CBD",
            "delivery_address_note": "Near the clock tower",
            "items": [
                {"product_id": "uuid", "quantity": 10}
            ]
        }
        """
        data = request.data
        fundi = get_object_or_404(Profile, id=data.get("fundi_id"), role="fundi")

        delivery_area = (data.get("delivery_area") or "").strip()
        if not delivery_area:
            return Response(
                {"detail": "Delivery area is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_data = data.get("items", [])
        if not items_data:
            return Response(
                {"detail": "Items are required."}, status=status.HTTP_400_BAD_REQUEST
            )

        first_product = get_object_or_404(Product, id=items_data[0].get("product_id"))
        store = first_product.store

        subtotal_hardware = Decimal("0")
        commission_total = Decimal("0")
        order_items_to_create = []

        for item in items_data:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 0)

            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return Response(
                    {
                        "detail": f"Quantity must be an integer for product {product_id}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if quantity < 1:
                return Response(
                    {
                        "detail": f"Quantity must be at least 1 for product {product_id}."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            product = get_object_or_404(Product, id=product_id, active=True)
            if product.store_id != store.id:
                return Response(
                    {"detail": "All items must belong to the same hardware store."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            commission_setting = (
                CommissionSetting.objects.filter(
                    category=product.category, unit=product.unit, active=True
                )
                .order_by("-effective_from")
                .first()
            )

            comm_per_unit = (
                commission_setting.commission_per_unit
                if commission_setting
                else Decimal("0")
            )
            hw_price = product.hardware_price_per_unit
            final_price = hw_price + comm_per_unit

            order_items_to_create.append(
                {
                    "product": product,
                    "quantity_units": quantity,
                    "hardware_price_per_unit": hw_price,
                    "commission_per_unit": comm_per_unit,
                    "final_price_per_unit": final_price,
                }
            )

            subtotal_hardware += hw_price * quantity
            commission_total += comm_per_unit * quantity

        with transaction.atomic():
            order = Order.objects.create(
                fundi=fundi,
                store=store,
                delivery_area=delivery_area,
                delivery_address_note=(data.get("delivery_address_note") or "").strip(),
                status="pending",
                payment_status="unpaid",
            )

            for item_payload in order_items_to_create:
                OrderItem.objects.create(order=order, **item_payload)

            order.subtotal_hardware = subtotal_hardware
            order.commission_total = commission_total
            order.grand_total = subtotal_hardware + commission_total
            order.save(
                update_fields=["subtotal_hardware", "commission_total", "grand_total"]
            )

            Notification.objects.create(
                user=store.owner,
                type="ORDER_CREATED",
                title="New Order Received",
                message=f"You have a new order #{order.short_id} from {fundi.full_name}",
                order=order,
            )

        # refresh and serialize
        order.refresh_from_db()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user.profile)

    @action(detail=False, methods=["post"])
    def mark_read(self, request):
        notification_ids = request.data.get("notification_ids", [])
        Notification.objects.filter(
            id__in=notification_ids, user=request.user.profile
        ).update(is_read=True)
        return Response({"status": "marked as read"})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(
            user=request.user.profile, is_read=False
        ).count()
        return Response({"unread_count": count})
