from decimal import Decimal

from rest_framework.test import APITestCase

from .models import Book


class BookDetailTests(APITestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Clean Code",
            author="Robert Martin",
            isbn="9780132350884",
            description="A handbook of agile software craftsmanship.",
            price=Decimal("499.00"),
            stock=5,
            cover="https://example.com/cover.jpg",
            genre="Programming",
        )
        self.url = f"/api/books/{self.book.id}/"

    def test_returns_all_required_fields(self):
        data = self.client.get(self.url).json()
        for field in ("title", "author", "price", "cover", "description", "stock"):
            self.assertIn(field, data)
        self.assertEqual(data["title"], "Clean Code")
        self.assertEqual(data["author"], "Robert Martin")
        self.assertEqual(data["price"], "499.00")
        self.assertEqual(data["stock"], 5)

    def test_has_reviews_placeholder(self):
        data = self.client.get(self.url).json()
        self.assertEqual(
            data["reviews"], {"average_rating": None, "count": 0, "items": []}
        )

    def test_cart_and_wishlist_available_when_in_stock(self):
        data = self.client.get(self.url).json()
        self.assertTrue(data["in_stock"])
        self.assertTrue(data["can_add_to_cart"])
        self.assertTrue(data["can_add_to_wishlist"])

    def test_cart_disabled_when_out_of_stock(self):
        self.book.stock = 0
        self.book.save()
        data = self.client.get(self.url).json()
        self.assertFalse(data["in_stock"])
        self.assertFalse(data["can_add_to_cart"])
        self.assertTrue(data["can_add_to_wishlist"])

    def test_unknown_book_returns_404(self):
        response = self.client.get("/api/books/99999/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "not_found")

    def test_guest_can_view(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
