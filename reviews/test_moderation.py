from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import AuditLog
from catalog.models import Book

from .models import Review

User = get_user_model()
URL = "/api/reviews/moderation/"


class ModerationTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create(username="mod", is_staff=True)
        self.buyer = User.objects.create(username="buyer")
        self.other = User.objects.create(username="other")
        self.book = Book.objects.create(
            title="Clean Code", author="Robert Martin", price=Decimal("100.00"), stock=5
        )
        self.good = Review.objects.create(user=self.buyer, book=self.book, rating=5, comment="Great")
        self.bad = Review.objects.create(user=self.other, book=self.book, rating=1, comment="Spam")
        self.client.force_authenticate(self.staff)

    def hide(self, review):
        return self.client.patch(f"{URL}{review.id}/", {"approved": False}, format="json")

    def test_anonymous_blocked(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(URL).status_code, (401, 403))
        self.assertIn(self.hide(self.bad).status_code, (401, 403))

    def test_normal_user_blocked(self):
        self.client.force_authenticate(self.buyer)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.hide(self.bad).status_code, 403)
        self.assertEqual(self.client.delete(f"{URL}{self.bad.id}/").status_code, 403)
        self.bad.refresh_from_db()
        self.assertTrue(self.bad.is_approved)

    def test_new_reviews_are_approved_by_default(self):
        self.assertTrue(self.good.is_approved)

    def test_hide_review(self):
        response = self.hide(self.bad)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["review"]["is_approved"])
        self.bad.refresh_from_db()
        self.assertFalse(self.bad.is_approved)
        self.assertEqual(self.bad.moderated_by, self.staff)
        self.assertIsNotNone(self.bad.moderated_at)

    def test_hidden_review_leaves_public_list_and_average(self):
        self.hide(self.bad)
        self.client.force_authenticate(None)
        data = self.client.get(f"/api/books/{self.book.id}/reviews/").json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["average_rating"], 5.0)
        self.assertEqual([r["id"] for r in data["results"]], [self.good.id])

    def test_hidden_review_leaves_book_detail(self):
        self.hide(self.bad)
        reviews = self.client.get(f"/api/books/{self.book.id}/").json()["reviews"]
        self.assertEqual(reviews["count"], 1)
        self.assertEqual(reviews["average_rating"], 5.0)

    def test_approve_restores_review(self):
        self.hide(self.bad)
        response = self.client.patch(f"{URL}{self.bad.id}/", {"approved": True}, format="json")
        self.assertEqual(response.status_code, 200)
        data = self.client.get(f"/api/books/{self.book.id}/reviews/").json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["average_rating"], 3.0)

    def test_book_with_only_hidden_reviews_has_no_average(self):
        self.hide(self.good)
        self.hide(self.bad)
        data = self.client.get(f"/api/books/{self.book.id}/reviews/").json()
        self.assertEqual((data["total"], data["average_rating"]), (0, None))

    def test_invalid_approved_value_rejected(self):
        for bad in (None, "maybe", 1, "yes"):
            with self.subTest(approved=bad):
                response = self.client.patch(
                    f"{URL}{self.bad.id}/", {"approved": bad}, format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_request")

    def test_unknown_review_404(self):
        self.assertEqual(self.hide(Review(id=99999)).status_code, 404)
        self.assertEqual(self.client.delete(f"{URL}99999/").status_code, 404)

    def test_list_defaults_to_hidden(self):
        self.hide(self.bad)
        data = self.client.get(URL).json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["id"], self.bad.id)
        self.assertEqual(data["results"][0]["book"]["title"], "Clean Code")

    def test_list_status_filters(self):
        self.hide(self.bad)
        ids = lambda state: {r["id"] for r in self.client.get(URL, {"status": state}).json()["results"]}
        self.assertEqual(ids("hidden"), {self.bad.id})
        self.assertEqual(ids("approved"), {self.good.id})
        self.assertEqual(ids("all"), {self.good.id, self.bad.id})

    def test_list_invalid_status_400(self):
        response = self.client.get(URL, {"status": "nope"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_status")

    def test_list_invalid_page_400(self):
        response = self.client.get(URL, {"page": "0"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_page")

    def test_delete_review(self):
        response = self.client.delete(f"{URL}{self.bad.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Review.objects.filter(pk=self.bad.id).exists())

    def test_actions_are_audited(self):
        self.hide(self.bad)
        self.client.patch(f"{URL}{self.bad.id}/", {"approved": True}, format="json")
        self.client.delete(f"{URL}{self.bad.id}/")
        events = list(
            AuditLog.objects.filter(username="mod").order_by("id").values_list("event", flat=True)
        )
        self.assertEqual(events, ["REVIEW_HIDDEN", "REVIEW_APPROVED", "REVIEW_DELETED"])
