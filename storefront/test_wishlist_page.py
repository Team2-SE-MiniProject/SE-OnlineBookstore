from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Book


class WishlistPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            title="Dune", author="Frank Herbert", price="499.00", stock=5
        )
        cls.user = get_user_model().objects.create_user(
            username="reader", password="Pass12345!"
        )

    def test_visitors_are_sent_to_log_in(self):
        response = self.client.get("/wishlist/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_logged_in_users_get_the_page(self):
        self.client.force_login(self.user)
        response = self.client.get("/wishlist/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="wishlist-grid"')

    def test_book_page_has_the_save_for_later_button(self):
        response = self.client.get(f"/books/{self.book.pk}/")
        self.assertContains(response, 'id="wishlist-button"')

    def test_wishlist_link_is_only_shown_to_logged_in_users(self):
        self.assertNotContains(self.client.get("/"), 'href="/wishlist/"')
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/"), 'href="/wishlist/"')