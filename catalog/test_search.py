from django.core.cache import cache
from decimal import Decimal
from rest_framework.test import APITestCase
from .models import Book
from django.contrib.auth import get_user_model
from reviews.models import Review


class SearchFilterSortTests(APITestCase):
    def setUp(self):
        cache.clear()

    url = "/api/books/"

    @classmethod
    def setUpTestData(cls):
        Book.objects.create(
            title="Dune", author="Frank Herbert", genre="Science Fiction",
            price=Decimal("499.00"), isbn="9780000000001",
        )
        Book.objects.create(
            title="The Hobbit", author="J.R.R. Tolkien", genre="Fantasy",
            price=Decimal("399.00"), isbn="9780000000002",
        )
        Book.objects.create(
            title="Clean Code", author="Robert C. Martin", genre="Programming",
            price=Decimal("599.00"), isbn="9780000000003",
        )

    def titles(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return [book["title"] for book in response.json()["results"]]

    # ---- search ----
    def test_search_by_title(self):
        self.assertEqual(self.titles(q="dune"), ["Dune"])

    def test_search_by_author(self):
        self.assertEqual(self.titles(q="tolkien"), ["The Hobbit"])

    def test_search_by_genre(self):
        self.assertEqual(self.titles(q="programming"), ["Clean Code"])

    def test_search_by_isbn(self):
        self.assertEqual(self.titles(q="9780000000003"), ["Clean Code"])

    def test_search_by_isbn_with_hyphens(self):
        self.assertEqual(self.titles(q="978-0-00-000000-3"), ["Clean Code"])

    def test_every_search_word_must_match(self):
        self.assertEqual(self.titles(q="frank dune"), ["Dune"])
        self.assertEqual(self.titles(q="frank hobbit"), [])

    def test_search_with_no_match_returns_empty_list(self):
        response = self.client.get(self.url, {"q": "zzzz"})
        self.assertEqual(response.json()["results"], [])
        self.assertEqual(response.json()["total"], 0)

    # ---- filter ----
    def test_filter_by_genre(self):
        self.assertEqual(self.titles(genre="fantasy"), ["The Hobbit"])

    def test_filter_by_price_range(self):
        self.assertEqual(self.titles(min_price="400", max_price="500"), ["Dune"])

    # ---- sort ----
    def test_default_sort_is_title(self):
        self.assertEqual(self.titles(), ["Clean Code", "Dune", "The Hobbit"])

    def test_sort_price_ascending(self):
        self.assertEqual(
            self.titles(sort="price_asc"), ["The Hobbit", "Dune", "Clean Code"]
        )

    def test_sort_price_descending(self):
        self.assertEqual(
            self.titles(sort="price_desc"), ["Clean Code", "Dune", "The Hobbit"]
        )

    def test_sort_newest_first(self):
        self.assertEqual(
            self.titles(sort="newest"), ["Clean Code", "The Hobbit", "Dune"]
        )
        
    def test_sort_by_rating_highest_first_unrated_last(self):
        User = get_user_model()
        u1 = User.objects.create_user(username="reader1", email="r1@example.com", password="Pass12345!")
        u2 = User.objects.create_user(username="reader2", email="r2@example.com", password="Pass12345!")
        dune = Book.objects.get(title="Dune")
        hobbit = Book.objects.get(title="The Hobbit")
        Review.objects.create(user=u1, book=dune, rating=3)
        Review.objects.create(user=u2, book=dune, rating=5)   # Dune averages 4
        Review.objects.create(user=u1, book=hobbit, rating=5)  # Hobbit averages 5
        self.assertEqual(
            self.titles(sort="rating"), ["The Hobbit", "Dune", "Clean Code"]
        )

    # ---- validation ----
    def test_invalid_sort_returns_400(self):
        response = self.client.get(self.url, {"sort": "banana"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_sort")

    def test_invalid_price_returns_400(self):
        for bad in ("abc", "NaN", "-5"):
            with self.subTest(min_price=bad):
                response = self.client.get(self.url, {"min_price": bad})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], "invalid_price")
