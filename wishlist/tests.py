from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from catalog.models import Book

from .models import WishlistItem

URL = "/api/wishlist/"


class WishlistTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="vidya", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")
        self.book1 = Book.objects.create(
            title="Clean Code", author="Robert Martin", price=Decimal("100.00"), stock=5
        )
        self.book2 = Book.objects.create(
            title="Refactoring", author="Martin Fowler", price=Decimal("250.50"), stock=0
        )
        self.client.force_authenticate(self.user)

    def add(self, book_id):
        return self.client.post(URL, {"bookId": book_id}, format="json")

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(URL).status_code, (401, 403))

    def test_empty_wishlist(self):
        data = self.client.get(URL).json()
        self.assertEqual(data, {"items": [], "total": 0})

    def test_add_book(self):
        response = self.add(self.book1.id)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["book"]["title"], "Clean Code")
        self.assertTrue(data["items"][0]["book"]["in_stock"])

    def test_out_of_stock_book_can_be_wishlisted(self):
        data = self.add(self.book2.id).json()
        self.assertFalse(data["items"][0]["book"]["in_stock"])

    def test_adding_twice_does_not_duplicate(self):
        self.add(self.book1.id)
        response = self.add(self.book1.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(WishlistItem.objects.filter(user=self.user).count(), 1)

    def test_add_unknown_book_returns_404(self):
        response = self.add(99999)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "book_not_found")

    def test_add_invalid_book_id_returns_400(self):
        for bad in (None, "abc", 0, -1):
            with self.subTest(bookId=bad):
                response = self.add(bad)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_request")

    def test_remove_book(self):
        self.add(self.book1.id)
        response = self.client.delete(f"{URL}{self.book1.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])

    def test_remove_book_not_in_wishlist_returns_404(self):
        response = self.client.delete(f"{URL}{self.book1.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "item_not_found")

    def test_wishlists_are_per_user(self):
        WishlistItem.objects.create(user=self.other, book=self.book1)
        self.assertEqual(self.client.get(URL).json()["total"], 0)
        # cannot remove another user's entry
        self.assertEqual(self.client.delete(f"{URL}{self.book1.id}/").status_code, 404)
        self.assertTrue(WishlistItem.objects.filter(user=self.other).exists())

    def test_wishlist_persists_across_sessions(self):
        self.add(self.book1.id)
        fresh_client = APIClient()  # a brand-new session
        fresh_client.force_authenticate(self.user)
        data = fresh_client.get(URL).json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["book"]["id"], self.book1.id)
