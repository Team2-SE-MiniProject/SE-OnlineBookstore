
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Book


class CatalogCachingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.book = Book.objects.create(
            title="Clean Code",
            author="Robert C. Martin",
            price=Decimal("599.00"),
            stock=10,
        )

    def tearDown(self):
        cache.clear()

    def test_catalog_response_is_cached(self):
        response1 = self.client.get("/api/books/")
        self.assertEqual(response1.status_code, 200)

        with patch("catalog.views.Book.objects.all") as mocked:
            response2 = self.client.get("/api/books/")
            self.assertEqual(response2.status_code, 200)
            mocked.assert_not_called()

    def test_different_query_parameters_use_separate_cache_entries(self):
        response1 = self.client.get("/api/books/")
        response2 = self.client.get("/api/books/", {"q": "Clean"})

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response1.json()["total"], 1)
        self.assertEqual(response2.json()["total"], 1)

    def test_book_detail_response_is_cached(self):
        url = f"/api/books/{self.book.pk}/"

        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)

        with patch("catalog.views.Book.objects.get") as mocked:
            response2 = self.client.get(url)
            self.assertEqual(response2.status_code, 200)
            mocked.assert_not_called()

    def test_different_books_have_separate_cache_entries(self):
        second_book = Book.objects.create(
            title="Dune",
            author="Frank Herbert",
            price=Decimal("499.00"),
            stock=5,
        )

        response1 = self.client.get(f"/api/books/{self.book.pk}/")
        response2 = self.client.get(f"/api/books/{second_book.pk}/")

        self.assertEqual(response1.json()["title"], "Clean Code")
        self.assertEqual(response2.json()["title"], "Dune")

    def test_cache_timeout_is_five_minutes(self):
        from django.conf import settings

        self.assertEqual(settings.CACHES["default"]["TIMEOUT"], 300)
