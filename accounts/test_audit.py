from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .audit import log_admin_action
from .models import AuditLog


class AdminAuditLoggingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="audit_admin",
            password="TestPassword123!",
            is_staff=True,
        )

    def test_admin_action_records_user_action_and_timestamp(self):
        before = timezone.now()

        log = log_admin_action(
            self.admin,
            "CREATED",
            "Book ID 42",
        )

        after = timezone.now()

        self.assertEqual(log.user, self.admin)
        self.assertEqual(log.username, "audit_admin")
        self.assertEqual(log.event, "ADMIN_ACTION")
        self.assertIn("CREATED", log.details)
        self.assertIn("Book ID 42", log.details)
        self.assertGreaterEqual(log.created_at, before)
        self.assertLessEqual(log.created_at, after)

    def test_unauthenticated_actor_is_not_logged(self):
        result = log_admin_action(None, "DELETED", "Book ID 42")

        self.assertIsNone(result)
        self.assertEqual(AuditLog.objects.count(), 0)


class AuditLogRetentionTests(TestCase):
    def test_cleanup_deletes_only_logs_older_than_one_year(self):
        User = get_user_model()
        admin = User.objects.create_user(username="retention_admin")

        old_log = AuditLog.objects.create(
            event="ADMIN_ACTION",
            user=admin,
            username=admin.username,
            details="Old action",
        )
        AuditLog.objects.filter(pk=old_log.pk).update(
            created_at=timezone.now() - timedelta(days=366)
        )

        recent_log = AuditLog.objects.create(
            event="ADMIN_ACTION",
            user=admin,
            username=admin.username,
            details="Recent action",
        )

        call_command("cleanup_audit_logs")

        self.assertFalse(AuditLog.objects.filter(pk=old_log.pk).exists())
        self.assertTrue(AuditLog.objects.filter(pk=recent_log.pk).exists())
