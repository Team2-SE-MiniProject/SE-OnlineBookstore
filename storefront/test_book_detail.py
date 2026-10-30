from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Book


class BookDetailPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            title="Dune", author="Frank Herbert", price="499.00", stock=5,
            genre="Science Fiction", description="A story about a desert planet.",
        )
        cls.sold_out = Book.objects.create(
            title="Gone", author="Someone", price="10.00", stock=0
        )

    def test_page_shows_the_book(self):
        response = self.client.get(f"/books/{self.book.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dune")
        self.assertContains(response, "Frank Herbert")
        self.assertContains(response, "A story about a desert planet.")
        self.assertContains(response, 'id="review-list"')

    def test_unknown_book_returns_404(self):
        self.assertEqual(self.client.get("/books/99999/").status_code, 404)

    def test_out_of_stock_book_says_so(self):
        response = self.client.get(f"/books/{self.sold_out.pk}/")
        self.assertContains(response, "Out of stock")

    def test_visitors_are_asked_to_log_in_to_review(self):
        response = self.client.get(f"/books/{self.book.pk}/")
        self.assertContains(response, f"/login/?next=/books/{self.book.pk}/")
        self.assertNotContains(response, 'id="review-form"')

    def test_logged_in_users_get_the_review_form(self):
        user = get_user_model().objects.create_user(username="reader", password="Pass12345!")
        self.client.force_login(user)
        response = self.client.get(f"/books/{self.book.pk}/")
        self.assertContains(response, 'id="review-form"')