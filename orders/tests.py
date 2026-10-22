from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Address
from cart.models import Cart, CartItem
from catalog.models import Book
from .models import Coupon, Order, OrderItem


class OrderModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
        )
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            price=Decimal("299.00"),
            stock=10,
        )

    def test_create_order(self):
        order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("299.00"),
        )
        order.books.add(self.book)

        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_amount, Decimal("299.00"))
        self.assertEqual(order.status, "pending")
        self.assertIn(self.book, order.books.all())


class CheckoutAPITest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="checkout-user",
            password="testpassword123",
        )
        self.other_user = User.objects.create_user(
            username="other-user",
            password="testpassword123",
        )
        self.book = Book.objects.create(
            title="Python for Beginners",
            author="Test Author",
            price=Decimal("299.00"),
            stock=10,
        )
        self.address = Address.objects.create(
            user=self.user,
            recipient_name="Test Buyer",
            line1="12 Test Street",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
        )
        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=self.cart,
            book=self.book,
            quantity=2,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/orders/checkout"

    def test_checkout_creates_pending_order_and_returns_payment_url(self):
        response = self.client.post(
            self.url,
            {"cartId": self.cart.pk, "addressId": self.address.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertTrue(response.data["orderId"])
        self.assertTrue(response.data["paymentUrl"])
        self.assertEqual(response.data["totalAmount"], "598.00")

        order = Order.objects.get(pk=response.data["orderId"])
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.delivery_address, self.address)
        self.assertEqual(order.total_amount, Decimal("598.00"))
        self.assertEqual(order.items.get(book=self.book).quantity, 2)

    def test_checkout_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url,
            {"cartId": self.cart.pk, "addressId": self.address.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_checkout_rejects_out_of_stock_book(self):
        self.book.stock = 1
        self.book.save(update_fields=["stock"])

        response = self.client.post(
            self.url,
            {"cartId": self.cart.pk, "addressId": self.address.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_checkout_rejects_another_users_address(self):
        other_address = Address.objects.create(
            user=self.other_user,
            recipient_name="Other Buyer",
            line1="99 Other Street",
            city="Mysuru",
            state="Karnataka",
            postal_code="570001",
            country="India",
        )

        response = self.client.post(
            self.url,
            {"cartId": self.cart.pk, "addressId": other_address.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Order.objects.filter(user=self.user).exists())

    def test_checkout_rejects_empty_cart(self):
        self.item.delete()
        response = self.client.post(
            self.url,
            {"cartId": self.cart.pk, "addressId": self.address.pk},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_checkout_applies_active_coupon(self):
        Coupon.objects.create(code="BOOK10", discount_percent=Decimal("10.00"))
        response = self.client.post(
            self.url,
            {
                "cartId": self.cart.pk,
                "addressId": self.address.pk,
                "couponCode": "book10",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["totalAmount"], "538.20")
        self.assertEqual(response.data["couponCode"], "BOOK10")

    def test_checkout_rejects_invalid_coupon(self):
        response = self.client.post(
            self.url,
            {
                "cartId": self.cart.pk,
                "addressId": self.address.pk,
                "couponCode": "NOT-REAL",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.filter(user=self.user).exists())
