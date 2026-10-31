"""
System test (Test Plan section 5): the whole customer journey, driven through
the real URLs.

Security tests (Test Plan section 5.1 and SRS BOOK-SR-001 to 005):
fuzzing, access control, CSRF, token tampering, password hashing,
no card data stored, and escaping of user-supplied text.
"""

import json
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import Address
from accounts.registration import verification_token
from catalog.models import Book
from orders.models import Order
from reviews.models import Review

FUZZ = [
    "' OR '1'='1",
    '"; DROP TABLE catalog_book; --',
    "<script>alert(1)</script>",
    "../../etc/passwd",
    "{{7*7}}",
    "A" * 5000,
    "unicode ✓ 😀",
    "   ",
    "-1",
    "99999999999999999999",
    "NaN",
    "1e999",
]


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
class FuzzTests(TestCase):
    """Odd input must be answered with a normal error, never a server crash (status 500)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="fuzzer", password="Pass12345!")
        cls.book = Book.objects.create(title="Dune", author="Frank Herbert", price="499.00", stock=5)

    def test_catalog_parameters_never_crash_the_server(self):
        for param in ("q", "genre", "sort", "page", "min_price", "max_price"):
            for value in FUZZ:
                with self.subTest(param=param, value=value[:20]):
                    response = self.client.get("/api/books/", {param: value})
                    self.assertLess(response.status_code, 500)

    def test_registration_fields_never_crash_the_server(self):
        good = {"username": "newuser", "email": "new@example.com", "password": "Str0ng!Pass#2026"}
        for field in good:
            for value in FUZZ:
                with self.subTest(field=field, value=value[:20]):
                    payload = dict(good, **{field: value})
                    response = post_json(Client(), "/accounts/register/", payload)
                    self.assertLess(response.status_code, 500)

    def test_login_fields_never_crash_the_server_or_let_anyone_in(self):
        for value in FUZZ:
            with self.subTest(value=value[:20]):
                response = Client().post("/accounts/login/", {"username": value, "password": value})
                self.assertLess(response.status_code, 500)
                self.assertNotEqual(response.status_code, 200)

    def test_address_fields_never_crash_the_server(self):
        good = {"recipient_name": "Zia", "line1": "12 MG Road", "line2": "", "city": "Bengaluru",
                "state": "Karnataka", "postal_code": "560001", "country": "India", "phone": "9876543210"}
        client = Client()
        client.force_login(self.user)
        for field in good:
            for value in FUZZ:
                with self.subTest(field=field, value=value[:20]):
                    response = post_json(client, "/api/addresses/", dict(good, **{field: value}))
                    self.assertLess(response.status_code, 500)

    def test_review_comments_never_crash_the_server(self):
        client = Client()
        client.force_login(self.user)
        for value in FUZZ:
            with self.subTest(value=value[:20]):
                response = post_json(
                    client, f"/api/books/{self.book.pk}/reviews/", {"rating": 5, "comment": value}
                )
                self.assertLess(response.status_code, 500)


class AccessControlTests(TestCase):
    """BOOK-SR-004: people can only reach what their role and account allow."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.alice = User.objects.create_user(username="alice", password="Pass12345!")
        cls.bob = User.objects.create_user(username="bob", password="Pass12345!")
        cls.book = Book.objects.create(title="Dune", author="Frank Herbert", price="499.00", stock=5)

    def logged_in(self, user):
        client = Client()
        client.force_login(user)
        return client

    def test_private_endpoints_need_a_login(self):
        client = Client()
        self.assertIn(client.get("/api/cart/").status_code, (401, 403))
        self.assertIn(client.get("/api/addresses/").status_code, (401, 403))
        response = post_json(client, "/api/orders/checkout", {"cartId": 1, "addressId": 1})
        self.assertIn(response.status_code, (401, 403))

    def test_the_admin_needs_staff_access(self):
        self.assertEqual(Client().get("/admin/").status_code, 302)
        self.assertEqual(self.logged_in(self.alice).get("/admin/").status_code, 302)

    def test_users_cannot_see_each_others_carts(self):
        post_json(self.logged_in(self.alice), "/api/cart/items/", {"bookId": self.book.pk, "quantity": 1})
        self.assertEqual(self.logged_in(self.bob).get("/api/cart/").json()["items"], [])

    def test_users_cannot_remove_each_others_cart_items(self):
        response = post_json(
            self.logged_in(self.alice), "/api/cart/items/", {"bookId": self.book.pk, "quantity": 1}
        )
        item_id = response.json()["items"][0]["id"]
        self.assertEqual(self.logged_in(self.bob).delete(f"/api/cart/items/{item_id}/").status_code, 404)

    def test_checkout_rejects_another_users_address(self):
        address = Address.objects.create(
            user=self.alice, recipient_name="Alice", line1="1 Road",
            city="Pune", state="Maharashtra", postal_code="411001",
        )
        bob = self.logged_in(self.bob)
        cart_id = post_json(bob, "/api/cart/items/", {"bookId": self.book.pk, "quantity": 1}).json()["id"]
        response = post_json(bob, "/api/orders/checkout", {"cartId": cart_id, "addressId": address.pk})
        self.assertEqual(response.status_code, 404)

    def test_a_tampered_token_is_rejected(self):
        client = Client()
        response = post_json(client, "/api/auth/login", {"username": "alice", "password": "Pass12345!"})
        token = response.json()["token"]
        tampered = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")
        response = client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Bearer {tampered}")
        self.assertIn(response.status_code, (401, 403))

    def test_csrf_protection_is_enforced_on_login(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/accounts/login/", {"username": "alice", "password": "Pass12345!"})
        self.assertEqual(response.status_code, 403)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.BCryptSHA256PasswordHasher"])
class DataProtectionTests(TestCase):
    """BOOK-SR-002 and BOOK-SR-003."""

    def test_passwords_are_stored_as_bcrypt_hashes(self):
        user = get_user_model().objects.create_user(username="hash-test", password="Pass12345!")
        self.assertTrue(user.password.startswith("bcrypt_sha256$"))
        self.assertNotIn("Pass12345!", user.password)

    def test_no_model_has_a_field_for_card_data(self):
        banned = ("card", "cvv", "cvc")
        offenders = [
            f"{model.__name__}.{field.name}"
            for model in apps.get_models()
            for field in model._meta.get_fields()
            if any(word in field.name.lower() for word in banned)
        ]
        self.assertEqual(offenders, [])


class OutputEscapingTests(TestCase):
    """Text typed by users or sellers must never run as HTML or script on the pages."""

    def test_book_details_are_escaped_on_the_detail_page(self):
        book = Book.objects.create(
            title="<script>alert(1)</script>", author="<b>x</b>", price="10.00", stock=1,
            description="<img src=x onerror=alert(1)>",
        )
        response = self.client.get(f"/books/{book.pk}/")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertNotContains(response, "<img src=x onerror=alert(1)>")
        self.assertContains(response, "&lt;script&gt;")
