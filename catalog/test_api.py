from decimal import Decimal

from rest_framework.test import APITestCase

from .models import Book


def make_books(n):
    Book.objects.bulk_create(
        [Book(title=f"Book {i:02d}", author="Author", price=Decimal("100.00")) for i in range(n)]
    )


class BookListTests(APITestCase):
    url = "/api/books/"

    def test_returns_expected_fields(self):
        make_books(1)
        data = self.client.get(self.url).json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total"], 1)
        self.assertEqual(
            set(data["results"][0]), {"id", "title", "author", "price", "cover"}
        )

    def test_page_size_is_20(self):
        make_books(25)
        data = self.client.get(self.url).json()
        self.assertEqual(len(data["results"]), 20)
        self.assertEqual(data["total"], 25)

    def test_second_page(self):
        make_books(25)
        data = self.client.get(self.url, {"page": 2}).json()
        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["page"], 2)

    def test_invalid_page_returns_400(self):
        for bad in ("abc", "0", "-1"):
            with self.subTest(page=bad):
                response = self.client.get(self.url, {"page": bad})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_page")

    def test_page_past_the_end_is_empty(self):
        make_books(3)
        data = self.client.get(self.url, {"page": 5}).json()
        self.assertEqual(data["results"], [])