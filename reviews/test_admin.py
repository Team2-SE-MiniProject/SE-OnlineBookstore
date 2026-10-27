from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Book

from .models import Review


class ReviewAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="boss", email="boss@example.com", password="Pass12345!"
        )
        reader = User.objects.create_user(
            username="reader", email="reader@example.com", password="Pass12345!"
        )
        book = Book.objects.create(title="Dune", author="Frank Herbert", price="499.00", stock=5)
        self.review = Review.objects.create(user=reader, book=book, rating=2, comment="Meh")
        self.client.force_login(self.admin_user)
        self.url = reverse("admin:reviews_review_changelist")

    def run_action(self, action):
        return self.client.post(
            self.url, {"action": action, "_selected_action": [self.review.pk]}
        )

    def test_hide_action_unapproves_the_review(self):
        self.run_action("hide_reviews")
        self.review.refresh_from_db()
        self.assertFalse(self.review.is_approved)

    def test_approve_action_restores_the_review(self):
        self.review.is_approved = False
        self.review.save()
        self.run_action("approve_reviews")
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_approved)

    def test_moderation_is_written_to_the_admin_log(self):
        self.run_action("hide_reviews")
        self.assertTrue(
            LogEntry.objects.filter(
                user=self.admin_user, object_id=str(self.review.pk)
            ).exists()
        )

    def test_changelist_can_filter_by_approval(self):
        response = self.client.get(self.url, {"is_approved__exact": "0"})
        self.assertEqual(response.status_code, 200)