from django.conf import settings
from django.db import models
from catalog.models import Book
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_reviews",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "book")

    def __str__(self):
        return f"{self.book} - {self.rating}/5"
    
@receiver([post_save, post_delete], sender=Review)
def clear_cache_when_a_review_changes(sender, **kwargs):
    cache.clear()  # cached book pages would otherwise show old ratings
