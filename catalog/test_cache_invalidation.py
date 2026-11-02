from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Book


class CacheInvalidationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.book = Book.objects.create(
            title="Dune", author="Frank Herbert", price="499.00", stock=5
        )

    def price_in_list(self):
        return self.client.get("/api/books/").json()["results"][0]["price"]

    def test_list_shows_a_price_change_straight_away(self):
        self.assertEqual(self.price_in_list(), "499.00")
        self.book.price = "399.00"
        self.book.save()
        self.assertEqual(self.price_in_list(), "399.00")

    def test_list_forgets_a_deleted_book_straight_away(self):
        self.assertEqual(len(self.client.get("/api/books/").json()["results"]), 1)
        self.book.delete()
        self.assertEqual(self.client.get("/api/books/").json()["results"], [])