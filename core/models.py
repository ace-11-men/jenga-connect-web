import uuid
import re
from django.db import models
from django.contrib.auth.models import User

_PRODUCT_WHITESPACE_RE = re.compile(r"\s+")
_PRODUCT_TOKEN_SPLIT_RE = re.compile(r"([-/+])")


def normalize_product_name(raw_name: str) -> str:
    if not raw_name:
        return ""

    compact_name = _PRODUCT_WHITESPACE_RE.sub(" ", raw_name).strip()
    if not compact_name:
        return ""

    normalized_tokens = []
    for token in compact_name.split(" "):
        parts = _PRODUCT_TOKEN_SPLIT_RE.split(token)
        normalized_parts = []

        for part in parts:
            if not part:
                continue
            if part in {"-", "/", "+"}:
                normalized_parts.append(part)
                continue

            if any(char.isdigit() for char in part):
                normalized_parts.append(part.upper())
            elif part.isupper() and len(part) <= 4:
                normalized_parts.append(part)
            else:
                normalized_parts.append(part[0].upper() + part[1:].lower())

        normalized_tokens.append("".join(normalized_parts))

    return " ".join(normalized_tokens)


class Profile(models.Model):
    ROLE_CHOICES = [
        ('fundi', 'Fundi'),
        ('hardware', 'Hardware Store'),
        ('admin', 'Admin'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='fundi')
    full_name = models.CharField(max_length=255)
    area = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"

class HardwareStore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='hardware_stores')
    name = models.CharField(max_length=255)
    area = models.CharField(max_length=255)
    delivery_capacity_units_per_day = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('cement', 'Cement'),
        ('building_blocks', 'Building Blocks'),
        ('iron_rods', 'Iron Rods'),
        ('plaster', 'Plaster'),
        ('paint_colour', 'Paint/Colour'),
    ]
    UNIT_CHOICES = [
        ('bag', 'Bag'),
        ('piece', 'Piece'),
        ('bar', 'Bar'),
        ('bucket', 'Bucket'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(HardwareStore, on_delete=models.CASCADE, related_name='products')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True, null=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    specs_json = models.JSONField(blank=True, null=True)
    hardware_price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    stock_units = models.IntegerField(default=0)
    delivery_eta_hours = models.IntegerField(default=24)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.name = normalize_product_name(self.name)
        super().save(*args, **kwargs)

        if not self.image:
            return

        try:
            from PIL import Image, UnidentifiedImageError
            img = Image.open(self.image.path)
            # Keep media lightweight for faster mobile pages.
            if img.height > 600 or img.width > 600:
                img.thumbnail((600, 600))
                img.save(self.image.path)
        except (FileNotFoundError, UnidentifiedImageError, OSError):
            # Ignore image processing failures to avoid blocking product saves.
            pass

    def __str__(self):
        return f"{self.name} - {self.store.name}"

class CommissionSetting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=50, choices=Product.CATEGORY_CHOICES)
    unit = models.CharField(max_length=20, choices=Product.UNIT_CHOICES)
    commission_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.category} ({self.unit}) - {self.commission_per_unit}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('rejected', 'Rejected'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    id = models.AutoField(primary_key=True)
    fundi = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='orders')
    store = models.ForeignKey(HardwareStore, on_delete=models.CASCADE, related_name='received_orders')
    delivery_area = models.CharField(max_length=255)
    delivery_address_note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    subtotal_hardware = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.short_id} - {self.status}"

    @property
    def short_id(self):
        return f"TXD{self.id:03d}"

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_units = models.IntegerField()
    hardware_price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    commission_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    final_price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity_units} x {self.product.name}"

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('tigopesa', 'Tigo Pesa'),
        ('airtelmoney', 'Airtel Money'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment_record')
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    phone_number = models.CharField(max_length=20)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='initiated')
    raw_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} - {self.method} - {self.status}"
