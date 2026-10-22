import logging

from django.test import TestCase, override_settings
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.test import APITestCase

from .exceptions import api_exception_handler
from .logging_filters import SensitiveDataFilter, redact

CONTEXT = {"request": None, "view": None}


class ErrorHandlerTests(TestCase):
    def test_not_authenticated(self):
        response = api_exception_handler(NotAuthenticated(), CONTEXT)
        self.assertEqual(response.data["code"], "not_authenticated")
        self.assertEqual(set(response.data), {"code", "message"})

    def test_permission_denied(self):
        response = api_exception_handler(PermissionDenied(), CONTEXT)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "forbidden")

    def test_validation_error_includes_details(self):
        exc = ValidationError({"email": ["Enter a valid email."]})
        response = api_exception_handler(exc, CONTEXT)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("email", response.data["details"])

    @override_settings(DEBUG=False)
    def test_unhandled_error_hides_details(self):
        with self.assertLogs("bookstore.exceptions", level="ERROR"):
            response = api_exception_handler(RuntimeError("internal detail"), CONTEXT)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["code"], "server_error")
        self.assertNotIn("internal detail", response.data["message"])


class ApiErrorFormatTests(APITestCase):
    def test_wrong_method_returns_code_and_message(self):
        response = self.client.post("/api/books/")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(set(response.json()), {"code", "message"})
        self.assertEqual(response.json()["code"], "method_not_allowed")


class LogRedactionTests(TestCase):
    def test_password_is_removed(self):
        self.assertNotIn("hunter2", redact("login failed password=hunter2"))

    def test_bearer_token_is_removed(self):
        self.assertNotIn("abc.def.ghi", redact("Authorization: Bearer abc.def.ghi"))

    def test_card_number_is_removed(self):
        self.assertNotIn("4111", redact("charged card 4111 1111 1111 1111 today"))

    def test_normal_text_is_untouched(self):
        self.assertEqual(redact("GET /api/books/ 200"), "GET /api/books/ 200")

    def test_filter_cleans_log_records(self):
        record = logging.LogRecord("x", logging.INFO, "", 0, "token=%s", ("abc123",), None)
        SensitiveDataFilter().filter(record)
        self.assertNotIn("abc123", record.getMessage())