from decimal import Decimal
from unittest.mock import patch

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
        gateway_patcher = patch("orders.views.create_payment_order", return_value={"id": "order_test_123"})
        gateway_patcher.start()
        self.addCleanup(gateway_patcher.stop)

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

class OrderHistoryAPITest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="history-user", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="other-history-user", password="testpass123"
        )

        self.book = Book.objects.create(
            title="History Test Book",
            author="Test Author",
            price=Decimal("299.00"),
            stock=10,
        )

        self.own_order = Order.objects.create(
            user=self.user,
            total_amount=Decimal("299.00"),
            status="shipped",
        )
        OrderItem.objects.create(
            order=self.own_order,
            book=self.book,
            quantity=1,
            unit_price=Decimal("299.00"),
        )

        self.other_order = Order.objects.create(
            user=self.other_user,
            total_amount=Decimal("598.00"),
            status="delivered",
        )
        OrderItem.objects.create(
            order=self.other_order,
            book=self.book,
            quantity=2,
            unit_price=Decimal("299.00"),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/orders/history"

    def test_buyer_sees_only_their_own_orders(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["orderId"], self.own_order.pk)

    def test_history_includes_status_total_and_items(self):
        response = self.client.get(self.url)

        order = response.data[0]
        self.assertEqual(order["status"], "shipped")
        self.assertEqual(order["totalAmount"], "299.00")
        self.assertEqual(len(order["items"]), 1)
        self.assertEqual(order["items"][0]["title"], "History Test Book")
        self.assertEqual(order["items"][0]["quantity"], 1)

    def test_empty_history_returns_empty_list(self):
        self.own_order.delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_history_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

from accounts.roles import assign_role
from orders.models import ReturnRefundRequest


class ReturnRefundRequestAPITest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            username="refund-buyer", password="testpass123"
        )
        self.other_buyer = User.objects.create_user(
            username="refund-other", password="testpass123"
        )
        self.seller = User.objects.create_user(
            username="refund-seller", password="testpass123"
        )
        self.admin = User.objects.create_superuser(
            username="refund-admin",
            email="refund-admin@example.com",
            password="testpass123",
        )

        assign_role(self.buyer, "buyer")
        assign_role(self.other_buyer, "buyer")
        assign_role(self.seller, "seller")

        self.book = Book.objects.create(
            title="Refund Test Book",
            author="Test Author",
            price=Decimal("100.00"),
            stock=5,
            seller=self.seller,
        )
        self.order = Order.objects.create(
            user=self.buyer,
            total_amount=Decimal("100.00"),
            status="DELIVERED",
        )
        OrderItem.objects.create(
            order=self.order,
            book=self.book,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)
        self.create_url = f"/api/orders/{self.order.pk}/return-refund"
        self.list_url = "/api/orders/return-refund-requests"

    def test_buyer_can_request_refund_for_delivered_order(self):
        response = self.client.post(
            self.create_url,
            {"reason": "The book arrived damaged."},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertTrue(
            ReturnRefundRequest.objects.filter(
                order=self.order, requested_by=self.buyer
            ).exists()
        )

    def test_request_rejected_if_order_not_delivered(self):
        self.order.status = "SHIPPED"
        self.order.save(update_fields=["status"])

        response = self.client.post(
            self.create_url,
            {"reason": "I changed my mind."},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ReturnRefundRequest.objects.exists())

    def test_buyer_cannot_request_refund_for_another_users_order(self):
        other_order = Order.objects.create(
            user=self.other_buyer,
            total_amount=Decimal("100.00"),
            status="DELIVERED",
        )

        response = self.client.post(
            f"/api/orders/{other_order.pk}/return-refund",
            {"reason": "Please refund."},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_reason_is_required(self):
        response = self.client.post(
            self.create_url,
            {"reason": "   "},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_buyer_can_view_own_request_status(self):
        refund_request = ReturnRefundRequest.objects.create(
            order=self.order,
            requested_by=self.buyer,
            reason="Damaged book",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], refund_request.pk)
        self.assertEqual(response.data[0]["status"], "PENDING")

    def test_seller_can_view_request_for_their_book(self):
        ReturnRefundRequest.objects.create(
            order=self.order,
            requested_by=self.buyer,
            reason="Damaged book",
        )
        self.client.force_authenticate(user=self.seller)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_admin_can_view_all_requests(self):
        ReturnRefundRequest.objects.create(
            order=self.order,
            requested_by=self.buyer,
            reason="Damaged book",
        )
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)