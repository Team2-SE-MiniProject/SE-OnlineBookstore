import re
from unittest.mock import patch
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import AuditLog

User = get_user_model()

REGISTER_URL = "/accounts/register/"
LOGIN_URL = "/accounts/login/"
PASSWORD = "StrongTestPass123!"


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
class RegistrationTests(TestCase):
    payload = {"username": "newbie", "email": "newbie@example.com", "password": PASSWORD}

    def register(self, **overrides):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(REGISTER_URL, {**self.payload, **overrides})

    def link_path(self):
        link = re.search(r"https?://\S+", mail.outbox[-1].body).group(0)
        return urlparse(link).path

    def login(self):
        return self.client.post(
            LOGIN_URL, {"username": "newbie", "password": PASSWORD}
        )

    # --- registration ---

    def test_registration_creates_inactive_user(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="newbie")
        self.assertFalse(user.is_active)
        self.assertEqual(user.email, "newbie@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)

    def test_registration_sends_verification_email(self):
        self.register()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["newbie@example.com"])
        self.assertIn("/accounts/verify/", mail.outbox[0].body)

    def test_registration_accepts_json_body(self):
        response = self.client.post(
            REGISTER_URL, self.payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)

    def test_registration_requires_post(self):
        self.assertEqual(self.client.get(REGISTER_URL).status_code, 405)

    def test_missing_fields_rejected(self):
        for field in ("username", "email", "password"):
            with self.subTest(missing=field):
                data = {k: v for k, v in self.payload.items() if k != field}
                response = self.client.post(REGISTER_URL, data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_request")
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_email_rejected(self):
        response = self.register(email="not-an-email")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_email")

    def test_invalid_username_rejected(self):
        response = self.register(username="bad name!")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_username")

    def test_weak_password_rejected(self):
        response = self.register(password="12345")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "weak_password")
        self.assertEqual(User.objects.count(), 0)

    def test_email_failure_does_not_break_registration(self):
        with patch("notifications.tasks.send_mail", side_effect=OSError("smtp down")):
            response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.count(), 1)

    # --- duplicates ---

    def test_duplicate_email_rejected(self):
        self.register()
        response = self.register(username="someoneelse")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "email_taken")
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_is_case_insensitive(self):
        self.register()
        response = self.register(username="someoneelse", email="NEWBIE@Example.com")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "email_taken")

    def test_duplicate_username_rejected(self):
        self.register()
        response = self.register(email="other@example.com")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "username_taken")

    # --- verification ---

    def test_unverified_account_cannot_log_in(self):
        self.register()
        response = self.login()
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_verification_link_activates_account(self):
        self.register()
        response = self.client.get(self.link_path())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.get(username="newbie").is_active)
        self.assertEqual(self.login().status_code, 200)

    def test_registration_and_verification_are_audited(self):
        self.register()
        self.client.get(self.link_path())
        events = set(
            AuditLog.objects.filter(username="newbie").values_list("event", flat=True)
        )
        self.assertEqual(events, {"USER_REGISTERED", "EMAIL_VERIFIED"})

    def test_verification_link_is_single_use(self):
        self.register()
        path = self.link_path()
        self.assertEqual(self.client.get(path).status_code, 200)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_link")

    def test_tampered_token_rejected(self):
        self.register()
        bad_path = self.link_path().rsplit("/", 2)[0] + "/bad-token/"
        response = self.client.get(bad_path)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.get(username="newbie").is_active)

    def test_garbage_uid_rejected(self):
        response = self.client.get("/accounts/verify/!!!/sometoken/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_link")

    def test_token_for_unknown_user_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(99999))
        response = self.client.get(f"/accounts/verify/{uid}/sometoken/")
        self.assertEqual(response.status_code, 400)
