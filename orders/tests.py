from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Book
from .models import Order


class OrderModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123"
        )
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            price=Decimal("299.00"),
            stock=10
        )

    def test_create_order(self):
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("299.00")
        )
        order.books.add(self.book)

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_amount, Decimal("299.00"))
        self.assertEqual(order.status, "pending")
        self.assertIn(self.book, order.books.all())
