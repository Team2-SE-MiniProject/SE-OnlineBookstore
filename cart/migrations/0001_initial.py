# Initial shopping-cart models.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="carts", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="CartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cart_items", to="catalog.book")),
                ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="cart.cart")),
            ],
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(fields=("cart", "book"), name="unique_book_per_cart"),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.CheckConstraint(condition=models.Q(("quantity__gte", 1)), name="cart_item_quantity_gte_1"),
        ),
    ]
