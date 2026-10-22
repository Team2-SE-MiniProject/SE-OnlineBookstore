from django.conf import settings
from django.db import models

from catalog.models import Book


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="wishlist_items"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "book"), name="unique_book_per_wishlist"
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.book.title}"
