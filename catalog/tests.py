from django.test import TestCase
from .models import Book
from decimal import Decimal

class BookModelTest(TestCase):
    def test_create_book(self):
        book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            description="A test description",
            price=Decimal("299.00"),
            stock=10,
            genre="Fiction"
        )

        self.assertEqual(book.title, "Test Book")
        self.assertEqual(book.author, "Test Author")
        self.assertEqual(book.price, Decimal("299.00"))
        self.assertEqual(book.stock, 10)

    def test_book_string_representation(self):
        book = Book.objects.create(
            title="Python Basics",
            author="Test Author",
            price="199.00",
            stock=5
        )

        self.assertEqual(str(book), "Python Basics")
