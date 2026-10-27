from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Book
from orders.models import Order
from reviews.models import Review

from .models import AccountLockout, AuditLog

User = get_user_model()


def url(model, view):
    """Admin URL for a model, for example url(Book, "changelist")."""
    return reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_{view}")


class AdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = User.objects.create_superuser(
            username="boss", email="boss@example.com", password="Pass12345!"
        )
        cls.reader = User.objects.create_user(
            username="reader", email="reader@example.com", password="Pass12345!"
        )
        cls.book = Book.objects.create(
            title="Dune", author="Frank Herbert", price="499.00", stock=5
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def run_user_action(self, action, *users):
        return self.client.post(
            url(User, "changelist"),
            {"action": action, "_selected_action": [user.pk for user in users]},
        )

    # ---- every screen opens ----
    def test_all_changelists_load(self):
        Review.objects.create(user=self.reader, book=self.book, rating=5)
        for model in (User, Book, Review, Order, LogEntry, AuditLog):
            with self.subTest(model=model.__name__):
                self.assertEqual(self.client.get(url(model, "changelist")).status_code, 200)

    def test_book_price_and_stock_can_be_edited_in_the_list(self):
        self.assertIn("price", admin.site._registry[Book].list_editable)
        self.assertIn("stock", admin.site._registry[Book].list_editable)

    # ---- bulk actions ----
    def test_deactivate_action_skips_the_admins_own_account(self):
        self.run_user_action("deactivate_users", self.reader, self.admin_user)
        self.reader.refresh_from_db()
        self.admin_user.refresh_from_db()
        self.assertFalse(self.reader.is_active)
        self.assertTrue(self.admin_user.is_active)

    def test_activate_action(self):
        self.reader.is_active = False
        self.reader.save()
        self.run_user_action("activate_users", self.reader)
        self.reader.refresh_from_db()
        self.assertTrue(self.reader.is_active)

    def test_unlock_action_clears_the_lockout(self):
        AccountLockout.objects.create(
            user=self.reader, failed_attempts=5,
            locked_until=timezone.now() + timedelta(minutes=15),
        )
        self.run_user_action("unlock_accounts", self.reader)
        lockout = AccountLockout.objects.get(user=self.reader)
        self.assertEqual(lockout.failed_attempts, 0)
        self.assertIsNone(lockout.locked_until)

    def test_bulk_action_is_written_to_the_admin_log(self):
        self.run_user_action("deactivate_users", self.reader)
        self.assertTrue(
            LogEntry.objects.filter(user=self.admin_user, object_id=str(self.reader.pk)).exists()
        )

    def test_mark_out_of_stock_action(self):
        self.client.post(
            url(Book, "changelist"),
            {"action": "mark_out_of_stock", "_selected_action": [self.book.pk]},
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.stock, 0)

    # ---- logs are read only ----
    def test_logs_cannot_be_added_from_the_admin(self):
        self.assertEqual(self.client.get(url(LogEntry, "add")).status_code, 403)
        self.assertEqual(self.client.get(url(AuditLog, "add")).status_code, 403)

    # ---- access ----
    def test_regular_users_cannot_open_the_admin(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])