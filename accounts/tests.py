from django.contrib.auth import get_user_model
from django.test import TestCase


class AuthenticationModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()

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
