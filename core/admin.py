from django.contrib import admin
from .models import (
    Profile,
    HardwareStore,
    Product,
    CommissionSetting,
    Order,
    OrderItem,
    Notification,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "phone", "role", "area", "created_at")
    list_filter = ("role", "area")
    search_fields = ("full_name", "phone", "user__username")


@admin.register(HardwareStore)
class HardwareStoreAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "area",
        "delivery_capacity_units_per_day",
        "active",
    )
    list_filter = ("active", "area")
    search_fields = ("name", "owner__full_name")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "store",
        "category",
        "unit",
        "hardware_price_per_unit",
        "stock_units",
        "active",
    )
    list_filter = ("category", "active", "unit")
    search_fields = ("name", "store__name")


@admin.register(CommissionSetting)
class CommissionSettingAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "unit",
        "commission_per_unit",
        "effective_from",
        "active",
    )
    list_filter = ("category", "active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "fundi", "store", "status", "grand_total", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "fundi__full_name", "store__name")
    inlines = [OrderItemInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read")
    search_fields = ("user__full_name", "title", "message")
