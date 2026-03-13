from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import (
    Profile,
    HardwareStore,
    Product,
    CommissionSetting,
    Order,
    OrderItem,
    Notification,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]  # Removed email for privacy


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ["id", "user", "phone", "role", "full_name", "area", "created_at"]
        read_only_fields = ["id", "created_at", "user"]


class HardwareStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareStore
        fields = [
            "id",
            "owner",
            "name",
            "area",
            "address",
            "latitude",
            "longitude",
            "delivery_capacity_units_per_day",
            "active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "store",
            "store_name",
            "category",
            "name",
            "brand",
            "description",
            "unit",
            "specs_json",
            "hardware_price_per_unit",
            "stock_units",
            "delivery_eta_hours",
            "image",
            "active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "store_name"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    products = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "quantity_units",
            "hardware_price_per_unit",
            "commission_per_unit",
            "final_price_per_unit",
            "products",
        ]
        read_only_fields = ["id", "product_id", "products"]

    def get_products(self, obj):
        return {"name": obj.product.name, "unit": obj.product.unit}


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(source="items", many=True, read_only=True)
    hardware_stores = serializers.SerializerMethodField()
    fundi_id = serializers.UUIDField(source="fundi.id", read_only=True)
    store_id = serializers.UUIDField(source="store.id", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "fundi_id",
            "store_id",
            "delivery_area",
            "delivery_address_note",
            "status",
            "subtotal_hardware",
            "commission_total",
            "grand_total",
            "created_at",
            "hardware_stores",
            "order_items",
        ]
        read_only_fields = ["id", "fundi_id", "store_id", "created_at"]

    def get_hardware_stores(self, obj):
        return {"name": obj.store.name}


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "type",
            "title",
            "message",
            "order",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
