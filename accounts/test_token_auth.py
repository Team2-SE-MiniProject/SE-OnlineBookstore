from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

FAST_HASHER = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # keeps the tests quick
BCRYPT = ["django.contrib.auth.hashers.BCryptSHA256PasswordHasher"]


@override_settings(PASSWORD_HASHERS=FAST_HASHER)
class TokenLoginTests(APITestCase):
    url = "/api/auth/login"

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader", email="reader@example.com", password="Pass12345!"
        )

    def post(self, **body):
        return self.client.post(self.url, body, format="json")

    def test_login_with_username_returns_token_and_role(self):
        response = self.post(username="reader", password="Pass12345!")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["role"], "buyer")
        self.assertTrue(data["token"])

    def test_login_with_email_works(self):
        response = self.post(email="Reader@Example.com", password="Pass12345!")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["token"])

    def test_superuser_gets_the_admin_role(self):
        get_user_model().objects.create_superuser(
            username="boss", email="boss@example.com", password="Pass12345!"
        )
        response = self.post(username="boss", password="Pass12345!")
        self.assertEqual(response.json()["role"], "admin")

    def test_wrong_password_returns_401(self):
        response = self.post(email="reader@example.com", password="wrong")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "invalid_credentials")

    def test_missing_fields_return_400(self):
        response = self.post(username="reader")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_request")

    def test_account_locks_after_five_failures(self):
        for _ in range(5):
            self.post(username="reader", password="wrong")
        response = self.post(username="reader", password="Pass12345!")  # even the right one
        self.assertEqual(response.status_code, 423)
        self.assertEqual(response.json()["code"], "account_locked")


@override_settings(PASSWORD_HASHERS=FAST_HASHER)
class TokenAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reader", email="reader@example.com", password="Pass12345!"
        )

    def get_token(self):
        response = self.client.post(
            "/api/auth/login", {"username": "reader", "password": "Pass12345!"}, format="json"
        )
        return response.json()["token"]

    def test_token_authenticates_requests(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.get_token())
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "reader")

    def test_token_works_on_the_cart_api(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.get_token())
        self.assertEqual(self.client.get("/api/cart/").status_code, 200)

    def test_garbage_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertIn(self.client.get("/api/auth/me").status_code, (401, 403))

    def test_expired_token_is_rejected(self):
        expired = jwt.encode(
            {"sub": str(self.user.pk), "exp": timezone.now() - timedelta(minutes=1)},
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + expired)
        self.assertIn(self.client.get("/api/auth/me").status_code, (401, 403))

    def test_no_token_is_rejected(self):
        self.assertIn(self.client.get("/api/auth/me").status_code, (401, 403))


@override_settings(PASSWORD_HASHERS=BCRYPT)
class PasswordHashingTests(TestCase):
    def test_new_passwords_are_stored_with_bcrypt(self):
        user = get_user_model().objects.create_user(username="hash-test", password="Pass12345!")
        self.assertTrue(user.password.startswith("bcrypt_sha256$"))
        self.assertTrue(user.check_password("Pass12345!"))