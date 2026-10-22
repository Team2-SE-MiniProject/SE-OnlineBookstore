from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import AccountLockout, AuditLog

class AuthenticationModelTest(TestCase):
def setUp(self):
self.User = get_user_model()

```
def test_create_user(self):
    user = self.User.objects.create_user(
        username="testuser",
        password="testpassword123",
    )
    self.assertEqual(user.username, "testuser")
    self.assertTrue(user.check_password("testpassword123"))

def test_password_is_not_stored_as_plain_text(self):
    user = self.User.objects.create_user(
        username="passworduser",
        password="testpassword123",
    )
    self.assertNotEqual(user.password, "testpassword123")
    self.assertTrue(user.check_password("testpassword123"))

def test_create_superuser(self):
    admin = self.User.objects.create_superuser(
        username="adminuser",
        password="testpassword123",
    )
    self.assertTrue(admin.is_staff)
    self.assertTrue(admin.is_superuser)
```

class AccountLockoutTests(TestCase):
def setUp(self):
User = get_user_model()
self.user = User.objects.create_user(
username="testuser",
password="StrongTestPass123!",
)
self.url = reverse("account-login")

```
def test_five_failed_attempts_lock_account(self):
    for _ in range(5):
        response = self.client.post(
            self.url,
            {"username": "testuser", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 401)

    lockout = AccountLockout.objects.get(user=self.user)
    self.assertEqual(lockout.failed_attempts, 5)
    self.assertIsNotNone(lockout.locked_until)

    remaining = lockout.locked_until - timezone.now()
    self.assertGreater(remaining, timedelta(minutes=14))
    self.assertLessEqual(remaining, timedelta(minutes=15))

    self.assertTrue(
        AuditLog.objects.filter(
            event="ACCOUNT_LOCKED",
            username="testuser",
        ).exists()
    )

def test_sixth_attempt_returns_423(self):
    for _ in range(5):
        self.client.post(
            self.url,
            {"username": "testuser", "password": "wrong-password"},
        )

    response = self.client.post(
        self.url,
        {"username": "testuser", "password": "StrongTestPass123!"},
    )
    self.assertEqual(response.status_code, 423)
    self.assertIn("error", response.json())

def test_successful_login_resets_failed_attempts(self):
    AccountLockout.objects.create(
        user=self.user,
        failed_attempts=3,
    )

    response = self.client.post(
        self.url,
        {"username": "testuser", "password": "StrongTestPass123!"},
    )

    self.assertEqual(response.status_code, 200)

    lockout = AccountLockout.objects.get(user=self.user)
    self.assertEqual(lockout.failed_attempts, 0)
    self.assertIsNone(lockout.locked_until)

def test_locked_account_rejects_login(self):
    AccountLockout.objects.create(
        user=self.user,
        failed_attempts=5,
        locked_until=timezone.now() + timedelta(minutes=15),
    )

    response = self.client.post(
        self.url,
        {"username": "testuser", "password": "StrongTestPass123!"},
    )

    self.assertEqual(response.status_code, 423)

def test_expired_lock_allows_login(self):
    AccountLockout.objects.create(
        user=self.user,
        failed_attempts=5,
        locked_until=timezone.now() - timedelta(minutes=1),
    )

    response = self.client.post(
        self.url,
        {"username": "testuser", "password": "StrongTestPass123!"},
    )

    self.assertEqual(response.status_code, 200)

    lockout = AccountLockout.objects.get(user=self.user)
    self.assertEqual(lockout.failed_attempts, 0)
    self.assertIsNone(lockout.locked_until)
```
