from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from catalog.models import Book

from .models import Cart, CartItem

CART_URL = "/api/cart/"
ITEMS_URL = "/api/cart/items/"


class CartTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="vidya", password="pass12345")
        self.other = User.objects.create_user(username="other", password="pass12345")
        self.book1 = Book.objects.create(
            title="Clean Code", author="Robert Martin", price=Decimal("100.00"), stock=5
        )
        self.book2 = Book.objects.create(
            title="Refactoring", author="Martin Fowler", price=Decimal("250.50"), stock=2
        )
        self.client.force_authenticate(self.user)

    def add(self, book, quantity=1):
        return self.client.post(
            ITEMS_URL, {"bookId": book.id, "quantity": quantity}, format="json"
        )

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(CART_URL).status_code, (401, 403))

    def test_empty_cart(self):
        data = self.client.get(CART_URL).json()
        self.assertEqual(data["items"], [])
        self.assertEqual(data["total_items"], 0)
        self.assertEqual(data["subtotal"], "0.00")
        self.assertTrue(Cart.objects.filter(user=self.user, is_active=True).exists())

    def test_add_item(self):
        response = self.add(self.book1, 2)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 2)
        self.assertEqual(data["items"][0]["book"]["title"], "Clean Code")
        self.assertEqual(data["subtotal"], "200.00")

    def test_add_defaults_to_quantity_one(self):
        response = self.client.post(ITEMS_URL, {"bookId": self.book1.id}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["items"][0]["quantity"], 1)

    def test_adding_same_book_increases_quantity(self):
        self.add(self.book1, 1)
        data = self.add(self.book1, 1).json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 2)

    def test_add_beyond_stock_rejected(self):
        response = self.add(self.book1, 6)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "insufficient_stock")

    def test_accumulated_quantity_beyond_stock_rejected(self):
        self.add(self.book2, 2)
        response = self.add(self.book2, 1)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "insufficient_stock")

    def test_add_unknown_book_returns_404(self):
        response = self.client.post(ITEMS_URL, {"bookId": 99999}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "book_not_found")

    def test_add_invalid_quantity_returns_400(self):
        for bad in (0, -1, "abc"):
            with self.subTest(quantity=bad):
                response = self.add(self.book1, bad)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_quantity")

    def test_update_quantity(self):
        item_id = self.add(self.book1, 1).json()["items"][0]["id"]
        response = self.client.patch(
            f"{ITEMS_URL}{item_id}/", {"quantity": 3}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["items"][0]["quantity"], 3)
        self.assertEqual(data["subtotal"], "300.00")

    def test_update_beyond_stock_rejected(self):
        item_id = self.add(self.book2, 1).json()["items"][0]["id"]
        response = self.client.patch(
            f"{ITEMS_URL}{item_id}/", {"quantity": 3}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "insufficient_stock")

    def test_remove_item(self):
        item_id = self.add(self.book1, 1).json()["items"][0]["id"]
        response = self.client.delete(f"{ITEMS_URL}{item_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertFalse(CartItem.objects.filter(pk=item_id).exists())

    def test_totals_with_multiple_books(self):
        self.add(self.book1, 2)
        data = self.add(self.book2, 1).json()
        self.assertEqual(data["total_items"], 3)
        self.assertEqual(data["subtotal"], "450.50")

    def test_cannot_change_another_users_item(self):
        other_cart = Cart.objects.create(user=self.other)
        item = CartItem.objects.create(cart=other_cart, book=self.book1, quantity=1)
        response = self.client.patch(
            f"{ITEMS_URL}{item.id}/", {"quantity": 2}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.delete(f"{ITEMS_URL}{item.id}/").status_code, 404)

    def test_cart_persists_across_sessions(self):
        self.add(self.book1, 2)
        self.client.force_authenticate(None)  # log out
        fresh_client = type(self.client)()  # a brand-new session
        fresh_client.force_authenticate(self.user)  # log back in
        data = fresh_client.get(CART_URL).json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["quantity"], 2)
        self.assertEqual(data["subtotal"], "200.00")
