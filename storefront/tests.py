from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import Address


class StorefrontPageTests(TestCase):
    def make_user(self):
        return get_user_model().objects.create_user(username="reader", password="Pass12345!")

    def test_home_page_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Online Bookstore")
        self.assertContains(response, 'id="book-grid"')

    def test_login_page_loads_and_links_to_register(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="login-form"')
        self.assertContains(response, 'href="/register/"')

    def test_register_page_loads(self):
        response = self.client.get("/register/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="register-form"')

    def test_nav_shows_register_to_visitors_only(self):
        self.assertContains(self.client.get("/"), 'href="/register/"')
        self.client.force_login(self.make_user())
        self.assertNotContains(self.client.get("/"), 'href="/register/"')

    def test_cart_page_redirects_anonymous_users_to_login(self):
        response = self.client.get("/cart/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_cart_page_loads_for_logged_in_user(self):
        self.client.force_login(self.make_user())
        response = self.client.get("/cart/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="cart-items"')

    def test_checkout_page_redirects_anonymous_users_to_login(self):
        response = self.client.get("/checkout/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_checkout_page_loads_for_logged_in_user(self):
        self.client.force_login(self.make_user())
        response = self.client.get("/checkout/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="place-order"')

    def test_logout_needs_post_and_ends_the_session(self):
        self.client.force_login(self.make_user())
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/")
        self.assertEqual(self.client.get("/cart/").status_code, 302)


class AddressApiTests(APITestCase):
    url = "/api/addresses/"
    payload = {
        "recipient_name": "Zia",
        "line1": "12 MG Road",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560001",
    }

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="reader", password="Pass12345!")
        self.other = User.objects.create_user(username="other", password="Pass12345!")
        self.client.force_authenticate(self.user)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_first_address_is_default_and_second_is_not(self):
        first = self.client.post(self.url, self.payload, format="json")
        second = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.json()["is_default"])
        self.assertFalse(second.json()["is_default"])
        self.assertEqual(Address.objects.filter(user=self.user).count(), 2)

    def test_list_shows_only_my_addresses(self):
        Address.objects.create(
            user=self.other, recipient_name="Other", line1="1 Street",
            city="Pune", state="Maharashtra", postal_code="411001",
        )
        self.client.post(self.url, self.payload, format="json")
        data = self.client.get(self.url).json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["recipient_name"], "Zia")

    def test_missing_fields_return_validation_error(self):
        response = self.client.post(self.url, {"city": "Pune"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")
        self.assertIn("line1", response.json()["details"])