"""
System test (Test Plan section 5): the whole customer journey, driven through the real URLs
the way the browser pages use them. The verification email is not sent in tests, so the
verification link is built from the same token generator the registration view uses.
"""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.registration import verification_token
from catalog.models import Book
from orders.models import Order
from reviews.models import Review


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


class CustomerJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.boss = User.objects.create_superuser(
            username="boss", email="boss@example.com", password="Pass12345!"
        )
        cls.dune = Book.objects.create(
            title="Dune", author="Frank Herbert", genre="Science Fiction",
            price="499.00", stock=5, isbn="9780441013593",
        )
        Book.objects.create(title="Emma", author="Jane Austen", genre="Classic", price="199.00", stock=3)
    @patch("orders.views.create_payment_order")
    def test_register_to_shipped_order_and_review(self, mock_create_payment_order):
        customer = Client()
        password = "Str0ng!Pass#2026"
        mock_create_payment_order.return_value = {
    "id": "order_test_123",
    "amount": 99800,
    "currency": "INR",
}

        # 1. Register. The account stays inactive until the emailed link is opened.
        response = post_json(
            customer, "/accounts/register/",
            {"username": "journey", "email": "journey@example.com", "password": password},
        )
        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(username="journey")
        self.assertFalse(user.is_active)

        # 2. Open the verification link, then log in.
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        link = f"/accounts/verify/{uid}/{verification_token.make_token(user)}/"
        self.assertEqual(customer.get(link).status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        response = customer.post("/accounts/login/", {"username": "journey", "password": password})
        self.assertEqual(response.status_code, 200)

        # 3. Search for a book and put two copies in the cart.
        results = customer.get("/api/books/", {"q": "dune"}).json()["results"]
        self.assertEqual([book["title"] for book in results], ["Dune"])

        response = post_json(customer, "/api/cart/items/", {"bookId": self.dune.pk, "quantity": 2})
        self.assertEqual(response.status_code, 201)
        cart = customer.get("/api/cart/").json()
        self.assertEqual(cart["total_items"], 2)
        self.assertEqual(cart["subtotal"], "998.00")

        # 4. Save a delivery address and check out.
        response = post_json(
            customer, "/api/addresses/",
            {"recipient_name": "Journey Tester", "line1": "12 MG Road", "city": "Bengaluru",
             "state": "Karnataka", "postal_code": "560001", "phone": "9876543210"},
        )
        self.assertEqual(response.status_code, 201)
        address_id = response.json()["id"]

        response = post_json(
            customer, "/api/orders/checkout", {"cartId": cart["id"], "addressId": address_id}
        )
        self.assertEqual(response.status_code, 201)
        order = response.json()
        self.assertEqual(order["status"], "PENDING")
        self.assertEqual(order["totalAmount"], "998.00")

        # 5. An admin ships the order from the admin dashboard.
        admin_client = Client()
        admin_client.force_login(self.boss)
        admin_client.post(
            reverse("admin:orders_order_changelist"),
            {"action": "mark_shipped", "_selected_action": [order["orderId"]]},
        )
        self.assertEqual(Order.objects.get(pk=order["orderId"]).status, "SHIPPED")

        # 6. The customer reviews the book, and an admin can hide the review.
        reviews_url = f"/api/books/{self.dune.pk}/reviews/"
        response = post_json(customer, reviews_url, {"rating": 5, "comment": "A classic."})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(customer.get(reviews_url).json()["results"]), 1)

        review = Review.objects.get(book=self.dune, user=user)
        admin_client.post(
            reverse("admin:reviews_review_changelist"),
            {"action": "hide_reviews", "_selected_action": [review.pk]},
        )
        self.assertEqual(customer.get(reviews_url).json()["results"], [])