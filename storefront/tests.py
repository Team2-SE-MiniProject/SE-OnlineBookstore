from django.contrib.auth import get_user_model
from django.test import TestCase


class StorefrontPageTests(TestCase):
    def make_user(self):
        return get_user_model().objects.create_user(username="reader", password="Pass12345!")

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Online Bookstore")
        self.assertContains(response, 'id="book-grid"')

    def test_login_page_loads(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="login-form"')

    def test_cart_page_redirects_anonymous_users_to_login(self):
        response = self.client.get("/cart/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_cart_page_loads_for_logged_in_user(self):
        self.client.force_login(self.make_user())
        response = self.client.get("/cart/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="cart-items"')

    def test_logout_needs_post_and_ends_the_session(self):
        self.client.force_login(self.make_user())
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/")
        self.assertEqual(self.client.get("/cart/").status_code, 302)