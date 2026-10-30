from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, OrderItem

from .models import Book


class SellerAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller_a = User.objects.create_user(username="sellera", password="Pass12345!")
        cls.seller_b = User.objects.create_user(username="sellerb", password="Pass12345!")
        cls.customer = User.objects.create_user(username="reader", password="Pass12345!")
        cls.boss = User.objects.create_superuser(
            username="boss", email="boss@example.com", password="Pass12345!"
        )
        call_command("make_seller", "sellera")
        call_command("make_seller", "sellerb")

        cls.book_a = Book.objects.create(
            title="Alpha Book", author="A", price="100.00", stock=3, seller=cls.seller_a
        )
        cls.book_b = Book.objects.create(
            title="Beta Book", author="B", price="200.00", stock=4, seller=cls.seller_b
        )
        cls.order_a = cls.make_order(cls.book_a)
        cls.order_b = cls.make_order(cls.book_b)

    @classmethod
    def make_order(cls, book):
        order = Order.objects.create(user=cls.customer, total_amount=book.price, status="PENDING")
        OrderItem.objects.create(order=order, book=book, quantity=1, unit_price=book.price)
        return order

    def titles_on(self, user, url_name):
        self.client.force_login(user)
        response = self.client.get(reverse(url_name))
        self.assertEqual(response.status_code, 200)
        return response.context["cl"].result_list

    # ---- books ----
    def test_seller_sees_only_their_own_books(self):
        books = self.titles_on(self.seller_a, "admin:catalog_book_changelist")
        self.assertEqual([book.title for book in books], ["Alpha Book"])

    def test_admin_sees_every_book(self):
        books = self.titles_on(self.boss, "admin:catalog_book_changelist")
        self.assertEqual(len(books), 2)

    def test_seller_cannot_open_another_sellers_book(self):
        self.client.force_login(self.seller_a)
        response = self.client.get(reverse("admin:catalog_book_change", args=[self.book_b.pk]))
        self.assertIn(response.status_code, (302, 404))

    def test_a_book_added_by_a_seller_belongs_to_them(self):
        self.client.force_login(self.seller_a)
        self.client.post(
            reverse("admin:catalog_book_add"),
            {"title": "New Book", "author": "Me", "isbn": "", "description": "",
             "price": "50.00", "stock": 2, "cover": "", "genre": ""},
        )
        self.assertEqual(Book.objects.get(title="New Book").seller, self.seller_a)

    def test_seller_cannot_open_the_user_admin(self):
        self.client.force_login(self.seller_a)
        response = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertEqual(response.status_code, 403)

    # ---- orders ----
    def test_seller_sees_only_orders_with_their_books(self):
        orders = self.titles_on(self.seller_a, "admin:orders_order_changelist")
        self.assertEqual(list(orders), [self.order_a])

    def run_action(self, user, action, *orders):
        self.client.force_login(user)
        return self.client.post(
            reverse("admin:orders_order_changelist"),
            {"action": action, "_selected_action": [order.pk for order in orders]},
        )

    def test_seller_can_ship_their_own_order(self):
        self.run_action(self.seller_a, "mark_shipped", self.order_a)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, "SHIPPED")

    def test_seller_cannot_ship_another_sellers_order(self):
        self.run_action(self.seller_a, "mark_shipped", self.order_b)
        self.order_b.refresh_from_db()
        self.assertEqual(self.order_b.status, "PENDING")

    def test_seller_cannot_cancel_orders(self):
        self.run_action(self.seller_a, "mark_cancelled", self.order_a)
        self.order_a.refresh_from_db()
        self.assertEqual(self.order_a.status, "PENDING")

    # ---- the make_seller command ----
    def test_make_seller_can_claim_unowned_books(self):
        orphan = Book.objects.create(title="Orphan", author="X", price="10.00", stock=1)
        call_command("make_seller", "sellera", "--claim-unowned-books")
        orphan.refresh_from_db()
        self.assertEqual(orphan.seller, self.seller_a)