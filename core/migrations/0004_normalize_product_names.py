import re
from django.db import migrations

_PRODUCT_WHITESPACE_RE = re.compile(r"\s+")
_PRODUCT_TOKEN_SPLIT_RE = re.compile(r"([-/+])")


def _normalize_product_name(raw_name: str) -> str:
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


def normalize_existing_product_names(apps, schema_editor):
    Product = apps.get_model('core', 'Product')
    for product in Product.objects.all().only('id', 'name'):
        normalized_name = _normalize_product_name(product.name)
        if normalized_name and normalized_name != product.name:
            Product.objects.filter(pk=product.pk).update(name=normalized_name)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_alter_order_id'),
    ]

    operations = [
        migrations.RunPython(normalize_existing_product_names, migrations.RunPython.noop),
    ]
