from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
import uuid
import re
import logging
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST
from .models import (
    Product,
    Profile,
    HardwareStore,
    Order,
    OrderItem,
    Payment,
    CommissionSetting,
    normalize_product_name,
)

logger = logging.getLogger(__name__)

PHONE_255_RE = re.compile(r"^255\d{9}$")
PHONE_0_RE = re.compile(r"^0\d{9}$")


def _normalize_phone_number(raw_phone: str) -> str:
    phone = (raw_phone or "").strip().replace(" ", "").replace("-", "").replace("+", "")
    if PHONE_0_RE.match(phone):
        return f"255{phone[1:]}"
    if PHONE_255_RE.match(phone):
        return phone
    return ""


def _parse_positive_decimal(raw_value):
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, TypeError):
        return None
    if value <= 0:
        return None
    return value


def home(request):
    category = request.GET.get("category")
    if category:
        products = Product.objects.filter(
            category=category, active=True
        ).select_related("store")
    else:
        products = Product.objects.filter(active=True).select_related("store")

    hardware_stores = HardwareStore.objects.filter(active=True)[:5]

    context = {"products": products, "hardware_stores": hardware_stores}
    return render(request, "home.html", context)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "product_detail.html", {"product": product})


@login_required
@require_POST
def checkout(request):
    profile = request.user.profile
    if profile.role != "fundi":
        messages.error(request, "Only fundi accounts can place orders.")
        return redirect("home")

    product_id = request.POST.get("product_id")
    delivery_area = (request.POST.get("delivery_area") or "").strip()
    address_note = (request.POST.get("address_note") or "").strip()
    quantity_raw = request.POST.get("quantity", "1")

    try:
        quantity = int(quantity_raw)
    except (TypeError, ValueError):
        messages.error(request, "Quantity must be a whole number.")
        return redirect("home")

    if quantity < 1:
        messages.error(request, "Quantity must be at least 1.")
        return redirect("home")

    if not delivery_area:
        messages.error(request, "Delivery area is required.")
        return redirect("home")

    product = get_object_or_404(Product, id=product_id, active=True)

    commission_setting = (
        CommissionSetting.objects.filter(
            category=product.category, unit=product.unit, active=True
        )
        .order_by("-effective_from")
        .first()
    )

    commission_per_unit = (
        commission_setting.commission_per_unit if commission_setting else Decimal("0")
    )
    hardware_price = product.hardware_price_per_unit
    final_price = hardware_price + commission_per_unit

    subtotal = hardware_price * quantity
    comm_total = commission_per_unit * quantity
    grand_total = final_price * quantity

    with transaction.atomic():
        order = Order.objects.create(
            fundi=profile,
            store=product.store,
            delivery_area=delivery_area,
            delivery_address_note=address_note,
            subtotal_hardware=subtotal,
            commission_total=comm_total,
            grand_total=grand_total,
            status="pending",
            payment_status="unpaid",
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity_units=quantity,
            hardware_price_per_unit=hardware_price,
            commission_per_unit=commission_per_unit,
            final_price_per_unit=final_price,
        )

    return redirect("initiate_payment", order_id=order.id)


@login_required
def initiate_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, fundi=request.user.profile)

    if request.method == "POST":
        method = (request.POST.get("method") or "").strip()
        phone = _normalize_phone_number(request.POST.get("phone"))

        valid_methods = {choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES}
        if method not in valid_methods:
            messages.error(request, "Invalid payment method selected.")
            return redirect("initiate_payment", order_id=order.id)

        if not phone:
            messages.error(
                request, "Enter a valid phone number (e.g. 07XXXXXXXX or 255XXXXXXXXX)."
            )
            return redirect("initiate_payment", order_id=order.id)

        existing_payment = Payment.objects.filter(order=order).first()
        if existing_payment and existing_payment.status == "completed":
            if order.payment_status != "paid" or order.status != "confirmed":
                order.payment_status = "paid"
                order.status = "confirmed"
                order.save(update_fields=["payment_status", "status"])
            messages.info(request, "This order has already been paid.")
            return redirect("dashboard")

        payment, _ = Payment.objects.update_or_create(
            order=order,
            defaults={
                "method": method,
                "phone_number": phone,
                "amount": order.grand_total,
                "status": "initiated",
                "transaction_id": None,
            },
        )

        if order.payment_status != "paid":
            order.payment_status = "processing"
            order.save(update_fields=["payment_status"])

        return render(
            request, "payment/processing.html", {"order": order, "payment": payment}
        )

    return render(request, "payment/select_method.html", {"order": order})


@login_required
@require_GET
def payment_status(request, payment_id):
    payment = get_object_or_404(
        Payment, id=payment_id, order__fundi=request.user.profile
    )

    if payment.status == "completed":
        return JsonResponse({"status": "success"})
    if payment.status == "failed":
        return JsonResponse({"status": "failed"})

    # Mock update: transition initiated -> completed
    if payment.status == "initiated":
        payment.status = "completed"
        payment.transaction_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        payment.save()

        order = payment.order
        order.payment_status = "paid"
        order.status = "confirmed"
        order.save()

        return JsonResponse({"status": "success"})

    return JsonResponse({"status": payment.status})


def user_login(request):
    if request.method == "POST":
        raw_phone = (request.POST.get("phone") or "").strip()
        normalized_phone = _normalize_phone_number(raw_phone)
        password = request.POST.get("password")

        if not raw_phone or not password:
            logger.warning(f"Login attempt with missing credentials")
            return render(
                request,
                "login.html",
                {"error": "Phone number and password are required."},
            )

        candidate_usernames = [raw_phone]
        if normalized_phone and normalized_phone != raw_phone:
            candidate_usernames.insert(0, normalized_phone)

        for username in candidate_usernames:
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                logger.info(f"User {username} logged in successfully")
                return redirect("dashboard")

        logger.warning(f"Failed login attempt for phone: {raw_phone}")
        return render(
            request, "login.html", {"error": "Invalid phone number or password."}
        )
    return render(request, "login.html")


def register(request):
    if request.method == "POST":
        full_name = (request.POST.get("full_name") or "").strip()
        raw_phone = request.POST.get("phone")
        phone = _normalize_phone_number(raw_phone)
        password = request.POST.get("password")
        role = request.POST.get("role")
        area = (request.POST.get("area") or "").strip()
        store_name = (request.POST.get("store_name") or "").strip()

        # Validation
        if not full_name or not area or not password:
            return render(
                request,
                "register.html",
                {"error": "All required fields must be filled."},
            )
        if not phone:
            return render(
                request,
                "register.html",
                {"error": "Use a valid phone number (07XXXXXXXX or 255XXXXXXXXX)."},
            )
        if len(password) < 6:
            return render(
                request,
                "register.html",
                {"error": "Password must be at least 6 characters long."},
            )
        if role == "hardware" and not store_name:
            return render(
                request,
                "register.html",
                {"error": "Store name is required for hardware accounts."},
            )

        if User.objects.filter(username=phone).exists():
            return render(
                request,
                "register.html",
                {"error": "Phone number already registered. Please login."},
            )

        try:
            with transaction.atomic():
                user = User.objects.create_user(username=phone, password=password)
                profile = Profile.objects.create(
                    user=user, phone=phone, full_name=full_name, role=role, area=area
                )

                if role == "hardware":
                    HardwareStore.objects.create(
                        owner=profile, name=store_name, area=area
                    )

                login(request, user)
                logger.info(f"New user registered with phone: {phone}, role: {role}")
                return redirect("dashboard")
        except Exception as e:
            logger.error(f"Error during registration for {phone}: {str(e)}")
            return render(
                request,
                "register.html",
                {"error": "An error occurred during registration. Please try again."},
            )

    return render(request, "register.html")


def user_logout(request):
    logout(request)
    return redirect("home")


@login_required
def dashboard(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        # Superuser maybe? Let's redirect admins to backend
        return redirect("/admin/")

    if profile.role == "fundi":
        orders = Order.objects.filter(fundi=profile).order_by("-created_at")
        return render(
            request, "dashboard/fundi.html", {"profile": profile, "orders": orders}
        )

    elif profile.role == "hardware":
        store = HardwareStore.objects.filter(owner=profile).first()
        if not store:
            return redirect("home")  # Fallback

        products = Product.objects.filter(store=store)
        orders = Order.objects.filter(store=store).order_by("-created_at")
        return render(
            request,
            "dashboard/hardware.html",
            {
                "profile": profile,
                "store": store,
                "products": products,
                "orders": orders,
            },
        )
    else:
        return redirect("manage_page")


@login_required
def add_product(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        logger.warning(f"User {request.user.username} has no profile")
        return redirect("dashboard")

    if profile.role != "hardware":
        logger.warning(
            f"Non-hardware user {request.user.username} tried to add product"
        )
        return redirect("dashboard")

    store = HardwareStore.objects.filter(owner=profile).first()
    if not store:
        logger.error(f"User {request.user.username} has no hardware store")
        messages.error(request, "You have no hardware store. Please contact support.")
        return redirect("dashboard")

    if request.method == "POST":
        category = request.POST.get("category")
        name = normalize_product_name(request.POST.get("name"))
        price = _parse_positive_decimal(request.POST.get("price"))
        unit = request.POST.get("unit")
        image = request.FILES.get("image")
        description = (request.POST.get("description") or "").strip() or None

        if not name:
            messages.error(request, "Product name is required.")
            return redirect("add_product")
        if price is None:
            messages.error(request, "Price must be a number greater than zero.")
            return redirect("add_product")
        if not category or not unit:
            messages.error(request, "Category and unit are required.")
            return redirect("add_product")

        try:
            Product.objects.create(
                store=store,
                category=category,
                name=name,
                description=description,
                hardware_price_per_unit=price,
                unit=unit,
                image=image,
                active=True,
            )
            logger.info(f"Product {name} added by {request.user.username}")
            messages.success(request, "Product added successfully!")
            return redirect("dashboard")
        except Exception as e:
            logger.error(f"Error adding product for {request.user.username}: {str(e)}")
            messages.error(
                request, "An error occurred while adding the product. Please try again."
            )
            return redirect("add_product")

    return render(request, "dashboard/add_product.html", {"store": store})


@login_required
@require_POST
def manage_order(request, order_id, action):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        logger.warning(f"User {request.user.username} has no profile")
        return redirect("dashboard")

    if profile.role != "hardware":
        logger.warning(
            f"Non-hardware user {request.user.username} tried to manage order"
        )
        return redirect("dashboard")

    order = get_object_or_404(Order, pk=order_id, store__owner=profile)

    status_by_action = {
        "confirm": "confirmed",
        "deliver": "delivered",
        "reject": "rejected",
    }
    new_status = status_by_action.get(action)
    if not new_status:
        logger.warning(f"Invalid action {action} attempted on order {order_id}")
        return HttpResponseBadRequest("Invalid order action.")

    try:
        old_status = order.status
        order.status = new_status
        order.save(update_fields=["status"])
        logger.info(
            f"Order {order_id} status changed from {old_status} to {new_status} by {request.user.username}"
        )
        messages.success(request, f"Order status updated to {new_status}.")
    except Exception as e:
        logger.error(f"Error updating order {order_id}: {str(e)}")
        messages.error(request, "An error occurred while updating the order.")

    return redirect("dashboard")


@login_required
@require_POST
def delete_product(request, product_id):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        logger.warning(f"User {request.user.username} has no profile")
        return redirect("dashboard")

    if profile.role != "hardware":
        logger.warning(
            f"Non-hardware user {request.user.username} tried to delete product"
        )
        return redirect("dashboard")

    store = HardwareStore.objects.filter(owner=profile).first()
    if not store:
        logger.error(f"User {request.user.username} has no hardware store")
        messages.error(request, "You have no hardware store.")
        return redirect("dashboard")

    product = get_object_or_404(Product, pk=product_id, store=store)

    try:
        product_name = product.name
        product.delete()
        logger.info(f"Product {product_name} deleted by {request.user.username}")
        messages.success(request, "Product deleted successfully!")
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {str(e)}")
        messages.error(request, "An error occurred while deleting the product.")

    return redirect("dashboard")


@login_required
def manage_page(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        if request.user.is_superuser:
            profile = Profile.objects.create(
                user=request.user,
                phone=request.user.username,
                full_name="Super Admin",
                role="admin",
                area="All",
            )
        else:
            return redirect("home")

    if profile.role not in ["admin", "hardware"]:
        return redirect("dashboard")

    if profile.role == "admin":
        stores = HardwareStore.objects.all()
    else:
        stores = HardwareStore.objects.filter(owner=profile)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_hardware" and profile.role == "admin":
            phone = _normalize_phone_number(request.POST.get("phone"))
            full_name = (request.POST.get("full_name") or "").strip()
            store_name = (request.POST.get("store_name") or "").strip()
            area = (request.POST.get("area") or "").strip()
            password = request.POST.get("password")

            if not all([phone, full_name, store_name, area, password]):
                messages.error(
                    request,
                    "All hardware fields are required with a valid phone number.",
                )
                return redirect("manage_page")

            user = User.objects.filter(username=phone).first()
            if not user:
                user = User.objects.create_user(username=phone, password=password)
                new_profile = Profile.objects.create(
                    user=user,
                    phone=phone,
                    full_name=full_name,
                    role="hardware",
                    area=area,
                )
            else:
                new_profile = Profile.objects.filter(user=user).first()
                if not new_profile:
                    new_profile = Profile.objects.create(
                        user=user,
                        phone=phone,
                        full_name=full_name,
                        role="hardware",
                        area=area,
                    )

            address = (request.POST.get("address") or "").strip()
            lat_raw = request.POST.get("latitude")
            lng_raw = request.POST.get("longitude")

            lat = None
            lng = None
            if lat_raw:
                try:
                    lat = float(lat_raw)
                except ValueError:
                    pass
            if lng_raw:
                try:
                    lng = float(lng_raw)
                except ValueError:
                    pass

            HardwareStore.objects.create(
                owner=new_profile,
                name=store_name,
                area=area,
                address=address or None,
                latitude=lat,
                longitude=lng,
            )
            return redirect("manage_page")

        elif action == "add_product":
            category = request.POST.get("category")
            name = normalize_product_name(request.POST.get("name"))
            price = _parse_positive_decimal(request.POST.get("price"))
            unit = request.POST.get("unit")
            image = request.FILES.get("image")
            description = (request.POST.get("description") or "").strip() or None

            if not name:
                messages.error(request, "Product name is required.")
                return redirect("manage_page")
            if price is None:
                messages.error(request, "Price must be a number greater than zero.")
                return redirect("manage_page")

            if profile.role == "admin":
                store_id = request.POST.get("store_id")
                store = get_object_or_404(HardwareStore, id=store_id)
            else:
                store = HardwareStore.objects.get(owner=profile)

            Product.objects.create(
                store=store,
                category=category,
                name=name,
                description=description,
                hardware_price_per_unit=price,
                unit=unit,
                image=image,
                active=True,
            )
            return redirect("manage_page")
        elif action == "delete_product":
            product_id = request.POST.get("product_id")

            if not product_id:
                messages.error(request, "Product ID is required.")
                return redirect("manage_page")

            if profile.role == "admin":
                product = get_object_or_404(Product, pk=product_id)
            else:
                store = HardwareStore.objects.filter(owner=profile).first()
                if not store:
                    logger.error(f"User {request.user.username} has no hardware store")
                    messages.error(request, "You have no hardware store.")
                    return redirect("manage_page")
                product = get_object_or_404(Product, pk=product_id, store=store)

            try:
                product_name = product.name
                product.delete()
                logger.info(
                    f"Product {product_name} deleted by {request.user.username} via manage page"
                )
                messages.success(request, "Product deleted successfully!")
            except Exception as e:
                logger.error(f"Error deleting product {product_id}: {str(e)}")
                messages.error(request, "An error occurred while deleting the product.")

            return redirect("manage_page")

    context = {
        "profile": profile,
        "stores": stores,
        "products": Product.objects.filter(store__in=stores).order_by("-created_at"),
    }
    return render(request, "dashboard/manage.html", context)


def map_view(request):
    stores = HardwareStore.objects.filter(
        active=True, latitude__isnull=False, longitude__isnull=False
    )
    stores_data = []
    for store in stores:
        stores_data.append(
            {
                "id": str(store.id),
                "name": store.name,
                "area": store.area,
                "address": store.address or "",
                "lat": store.latitude,
                "lng": store.longitude,
                "delivery_capacity": store.delivery_capacity_units_per_day,
            }
        )
    return render(request, "map.html", {"stores": stores_data})
