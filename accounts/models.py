from django.conf import settings
from django.db import models
from django.utils import timezone


class AccountLockout(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_lockout",
    )
    failed_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_locked(self):
        return (
            self.locked_until is not None
            and self.locked_until > timezone.now()
        )

    def __str__(self):
        return f"Lockout status for {self.user}"


class AuditLog(models.Model):
    event = models.CharField(max_length=100)
    username = models.CharField(max_length=150, db_index=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event} - {self.username}"
