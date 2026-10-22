from django.conf import settings
from django.db import models

from accounts.models import Address
from catalog.models import Book


class Coupon(models.Model):
    """Simple percentage coupon used by the checkout endpoint."""

    code = models.CharField(max_length=40, unique=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    books = models.ManyToManyField(Book, related_name="orders")
    delivery_address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("order", "book"), name="unique_book_per_order"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="order_item_quantity_gte_1"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.book.title} (order {self.order_id})"
