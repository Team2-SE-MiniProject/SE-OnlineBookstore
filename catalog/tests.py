from decimal import Decimal

from django.test import TestCase

from .models import Book


class BookModelTest(TestCase):
    def test_create_book(self):
        book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            description="A test description",
            price=Decimal("299.00"),
            stock=10,
            genre="Fiction",
        )

        self.assertEqual(book.title, "Test Book")
        self.assertEqual(book.author, "Test Author")
        self.assertEqual(book.price, Decimal("299.00"))
        self.assertEqual(book.stock, 10)
        self.assertEqual(book.genre, "Fiction")

    def test_book_string_representation(self):
        book = Book.objects.create(
            title="Python Basics",
            author="Test Author",
            price=Decimal("199.00"),
            stock=5,
        )

        self.assertEqual(str(book), "Python Basics")

    def test_book_default_stock_is_zero(self):
        book = Book.objects.create(
            title="New Book",
            author="Test Author",
            price=Decimal("99.00"),
        )

        self.assertEqual(book.stock, 0)

    def test_book_optional_fields_can_be_blank(self):
        book = Book.objects.create(
            title="Minimal Book",
            author="Test Author",
            price=Decimal("99.00"),
        )

        self.assertEqual(book.description, "")
        self.assertEqual(book.genre, "")
        self.assertEqual(book.cover, "")

    def test_books_are_ordered_by_title(self):
        Book.objects.create(
            title="Zebra Book",
            author="Author Z",
            price=Decimal("100.00"),
        )
        Book.objects.create(
            title="Apple Book",
            author="Author A",
            price=Decimal("100.00"),
        )

        titles = list(
            Book.objects.values_list("title", flat=True)
        )

        self.assertEqual(titles, ["Apple Book", "Zebra Book"])