from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from catalog.models import Book

from .models import Review

User = get_user_model()


def make_user(name):
    return User.objects.create(username=name)


class ReviewApiTests(APITestCase):
    def setUp(self):
        self.user = make_user("vidya")
        self.other = make_user("other")
        self.book = Book.objects.create(
            title="Clean Code", author="Robert Martin", price=Decimal("100.00"), stock=5
        )
        self.url = f"/api/books/{self.book.id}/reviews/"
        self.client.force_authenticate(self.user)

    def post(self, **data):
        return self.client.post(self.url, data, format="json")

    # --- listing ---

    def test_list_empty(self):
        data = self.client.get(self.url).json()
        self.assertEqual(
            data, {"average_rating": None, "total": 0, "page": 1, "results": []}
        )

    def test_list_shows_reviews_and_average(self):
        Review.objects.create(user=self.user, book=self.book, rating=5, comment="Great")
        Review.objects.create(user=self.other, book=self.book, rating=4)
        self.client.force_authenticate(None)  # guests can read
        data = self.client.get(self.url).json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["average_rating"], 4.5)
        self.assertEqual(
            set(data["results"][0]), {"id", "user", "rating", "comment", "created_at"}
        )

    def test_list_unknown_book_404(self):
        response = self.client.get("/api/books/99999/reviews/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "book_not_found")

    def test_list_invalid_page_400(self):
        for bad in ("abc", "0", "-1"):
            with self.subTest(page=bad):
                response = self.client.get(self.url, {"page": bad})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_page")

    def test_list_pagination(self):
        users = User.objects.bulk_create([User(username=f"u{i}") for i in range(25)])
        Review.objects.bulk_create(
            [Review(user=u, book=self.book, rating=5) for u in users]
        )
        first = self.client.get(self.url).json()
        self.assertEqual(len(first["results"]), 20)
        self.assertEqual(first["total"], 25)
        self.assertEqual(len(self.client.get(self.url, {"page": 2}).json()["results"]), 5)
        self.assertEqual(self.client.get(self.url, {"page": 3}).json()["results"], [])

    # --- creating ---

    def test_create_requires_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.post(rating=5).status_code, (401, 403))
        self.assertEqual(Review.objects.count(), 0)

    def test_create_review(self):
        response = self.post(rating=5, comment="  Great book!  ")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["review"]["rating"], 5)
        self.assertEqual(data["review"]["comment"], "Great book!")
        self.assertEqual(data["review"]["user"], "vidya")
        self.assertEqual(data["average_rating"], 5.0)
        self.assertEqual(data["total"], 1)

    def test_create_without_comment(self):
        response = self.post(rating=3)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["review"]["comment"], "")

    def test_invalid_rating_rejected(self):
        for bad in (0, 6, -1, "abc", 4.5, None, True):
            with self.subTest(rating=bad):
                response = self.post(rating=bad)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_rating")
        self.assertEqual(Review.objects.count(), 0)

    def test_comment_too_long(self):
        response = self.post(rating=5, comment="x" * 2001)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_comment")

    def test_comment_must_be_text(self):
        response = self.post(rating=5, comment=123)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_comment")

    def test_duplicate_review_409(self):
        self.post(rating=5)
        response = self.post(rating=1)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "already_reviewed")
        self.assertEqual(Review.objects.filter(user=self.user).count(), 1)

    def test_review_unknown_book_404(self):
        response = self.client.post(
            "/api/books/99999/reviews/", {"rating": 5}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "book_not_found")

    # --- editing and deleting ---

    def test_update_own_review(self):
        review = Review.objects.create(user=self.user, book=self.book, rating=2)
        response = self.client.patch(
            f"{self.url}{review.id}/", {"rating": 4, "comment": "Better"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual((review.rating, review.comment), (4, "Better"))
        self.assertEqual(response.json()["average_rating"], 4.0)

    def test_update_requires_a_field(self):
        review = Review.objects.create(user=self.user, book=self.book, rating=2)
        response = self.client.patch(f"{self.url}{review.id}/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_request")

    def test_cannot_update_others_review(self):
        review = Review.objects.create(user=self.other, book=self.book, rating=2)
        response = self.client.patch(
            f"{self.url}{review.id}/", {"rating": 5}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        review.refresh_from_db()
        self.assertEqual(review.rating, 2)

    def test_delete_own_review(self):
        review = Review.objects.create(user=self.user, book=self.book, rating=2)
        response = self.client.delete(f"{self.url}{review.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"average_rating": None, "total": 0})
        self.assertFalse(Review.objects.filter(pk=review.id).exists())

    def test_cannot_delete_others_review(self):
        review = Review.objects.create(user=self.other, book=self.book, rating=2)
        response = self.client.delete(f"{self.url}{review.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Review.objects.filter(pk=review.id).exists())

    # --- book detail page (replaces the Sprint 1 placeholder) ---

    def test_book_detail_shows_review_summary(self):
        Review.objects.create(user=self.user, book=self.book, rating=5, comment="Great")
        Review.objects.create(user=self.other, book=self.book, rating=4)
        reviews = self.client.get(f"/api/books/{self.book.id}/").json()["reviews"]
        self.assertEqual(reviews["average_rating"], 4.5)
        self.assertEqual(reviews["count"], 2)
        self.assertEqual(len(reviews["items"]), 2)

    def test_average_rounds_to_one_decimal(self):
        third = make_user("third")
        for user, rating in ((self.user, 5), (self.other, 5), (third, 4)):
            Review.objects.create(user=user, book=self.book, rating=rating)
        self.assertEqual(self.client.get(self.url).json()["average_rating"], 4.7)
