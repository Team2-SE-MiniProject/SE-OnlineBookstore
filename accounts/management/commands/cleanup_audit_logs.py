from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import AuditLog


class Command(BaseCommand):
    help = "Delete audit logs older than one year."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=365)
        deleted_count, _ = AuditLog.objects.filter(
            created_at__lt=cutoff
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted_count} old audit log record(s)."
            )
        )
