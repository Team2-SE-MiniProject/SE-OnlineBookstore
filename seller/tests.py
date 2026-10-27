from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Book
from orders.models import Order, OrderItem

from . import services

User = get_user_model()


def aware(year, month, day=15):
    return timezone.make_aware(datetime(year, month, day, 12, 0))


def make_seller(username):
    user = User.objects.create_user(username, password="pass-12345")
    user.groups.add(Group.objects.get(name="Seller"))
    return user


def make_book(seller, title="Book", price="100.00", stock=10, **extra):
    return Book.objects.create(seller=seller, title=title, author="Author", price=Decimal(price), stock=stock, **extra)


def make_sale(book, qty, when, status="PAID", unit_price=None, buyer=None):
    buyer = buyer or User.objects.get_or_create(username="buyer")[0]
    order = Order.objects.create(user=buyer, total_amount=Decimal("0"), status=status)
    Order.objects.filter(pk=order.pk).update(created_at=when)
    OrderItem.objects.create(order=order, book=book, quantity=qty, unit_price=Decimal(unit_price or book.price))
    return order


class SellerTestCase(TestCase):
    def setUp(self):
        self.alice = make_seller("alice")
        self.bob = make_seller("bob")
        self.customer = User.objects.create_user("customer", password="pass-12345")


class AccessTests(SellerTestCase):
    def test_seller_group_exists(self):
        self.assertTrue(Group.objects.filter(name="Seller").exists())

    def test_anonymous_is_sent_to_login(self):
        for name in ("seller:dashboard", "seller:analytics", "seller:book-add", "seller:analytics-export"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("storefront:login"), response["Location"], name)

    def test_customer_without_seller_group_gets_403(self):
        self.client.force_login(self.customer)
        for name in ("seller:dashboard", "seller:analytics", "seller:book-add", "seller:analytics-export"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_seller_and_superuser_allowed(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("seller:dashboard")).status_code, 200)
        admin = User.objects.create_superuser("root", password="pass-12345")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("seller:analytics")).status_code, 200)


class ListingCrudTests(SellerTestCase):
    def valid_data(self, **over):
        data = {"title": "New Book", "author": "Writer", "isbn": "123", "genre": "Fiction",
                "description": "d", "price": "499.00", "stock": "7", "cover": ""}
        data.update(over)
        return data

    def test_seller_can_add_book_and_becomes_owner(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("seller:book-add"), self.valid_data())
        self.assertRedirects(response, reverse("seller:dashboard"))
        book = Book.objects.get(title="New Book")
        self.assertEqual(book.seller, self.alice)

    def test_cannot_set_owner_through_form(self):
        self.client.force_login(self.alice)
        self.client.post(reverse("seller:book-add"), self.valid_data(seller=self.bob.pk))
        self.assertEqual(Book.objects.get(title="New Book").seller, self.alice)

    def test_invalid_price_and_title_rejected(self):
        self.client.force_login(self.alice)
        for bad in ({"price": "0"}, {"price": "-5"}, {"title": "   "}, {"stock": "-1"}):
            response = self.client.post(reverse("seller:book-add"), self.valid_data(**bad))
            self.assertEqual(response.status_code, 200, bad)
            self.assertEqual(Book.objects.count(), 0, bad)

    def test_form_errors_are_announced_and_linked(self):
        self.client.force_login(self.alice)
        response = self.client.post(reverse("seller:book-add"), self.valid_data(price="0"))
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'aria-describedby="id_price_hint id_price_error"')

    def test_seller_can_edit_stock_and_price(self):
        book = make_book(self.alice, price="100.00", stock=3)
        self.client.force_login(self.alice)
        response = self.client.post(reverse("seller:book-edit", args=[book.pk]),
                                    self.valid_data(title=book.title, price="250.50", stock="40"))
        self.assertRedirects(response, reverse("seller:dashboard"))
        book.refresh_from_db()
        self.assertEqual((book.price, book.stock), (Decimal("250.50"), 40))

    def test_seller_can_delete_own_book(self):
        book = make_book(self.alice)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("seller:book-delete", args=[book.pk])).status_code, 200)
        self.client.post(reverse("seller:book-delete", args=[book.pk]))
        self.assertFalse(Book.objects.filter(pk=book.pk).exists())

    def test_seller_cannot_touch_another_sellers_book(self):
        book = make_book(self.bob, title="Bobs", price="100.00", stock=5)
        self.client.force_login(self.alice)
        for name in ("seller:book-edit", "seller:book-delete"):
            self.assertEqual(self.client.get(reverse(name, args=[book.pk])).status_code, 404, name)
        self.client.post(reverse("seller:book-edit", args=[book.pk]), self.valid_data(title="Hacked"))
        self.client.post(reverse("seller:book-delete", args=[book.pk]))
        book.refresh_from_db()
        self.assertEqual((book.title, book.price, book.stock), ("Bobs", Decimal("100.00"), 5))

    def test_ordered_book_is_not_deleted_and_user_is_told(self):
        book = make_book(self.alice)
        make_sale(book, 1, aware(2026, 10))
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("seller:book-delete", args=[book.pk])), "cannot be deleted")
        response = self.client.post(reverse("seller:book-delete", args=[book.pk]), follow=True)
        self.assertTrue(Book.objects.filter(pk=book.pk).exists())
        self.assertContains(response, "cannot be deleted")

    def test_delete_requires_post(self):
        book = make_book(self.alice)
        self.client.force_login(self.alice)
        self.client.get(reverse("seller:book-delete", args=[book.pk]))
        self.assertTrue(Book.objects.filter(pk=book.pk).exists())


class DashboardTests(SellerTestCase):
    def test_only_own_books_listed(self):
        make_book(self.alice, title="Alice One")
        make_book(self.bob, title="Bob One")
        self.client.force_login(self.alice)
        response = self.client.get(reverse("seller:dashboard"))
        self.assertContains(response, "Alice One")
        self.assertNotContains(response, "Bob One")

    def test_search_and_empty_state(self):
        make_book(self.alice, title="Python Tricks", genre="Programming")
        make_book(self.alice, title="Gardening")
        self.client.force_login(self.alice)
        response = self.client.get(reverse("seller:dashboard"), {"q": "python"})
        self.assertContains(response, "Python Tricks")
        self.assertNotContains(response, "Gardening")
        self.assertContains(self.client.get(reverse("seller:dashboard"), {"q": "zzz"}), "No books match")

    def test_kpis_and_stock_labels_use_text_not_colour_only(self):
        make_book(self.alice, title="A", stock=0)
        make_book(self.alice, title="B", stock=3)
        make_book(self.alice, title="C", stock=50)
        k = services.inventory_kpis(self.alice)
        self.assertEqual((k["titles"], k["units"], k["low_stock"], k["out_of_stock"]), (3, 53, 1, 1))
        self.client.force_login(self.alice)
        response = self.client.get(reverse("seller:dashboard"))
        for label in ("Out of stock", "Low stock", "In stock"):
            self.assertContains(response, label)

    def test_recent_orders_show_only_sellers_share(self):
        mine = make_book(self.alice, price="100.00")
        theirs = make_book(self.bob, price="900.00")
        order = make_sale(mine, 2, aware(2026, 10))
        OrderItem.objects.create(order=order, book=theirs, quantity=1, unit_price=Decimal("900.00"))
        rows = services.recent_orders(self.alice)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].seller_total, Decimal("200.00"))


class AnalyticsTests(SellerTestCase):
    TODAY = date(2026, 10, 27)

    def test_month_starts_cross_year(self):
        self.assertEqual(services.month_starts(3, date(2026, 1, 20)),
                         [date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1)])
        self.assertEqual(len(services.month_starts(12, self.TODAY)), 12)

    def test_parse_range_falls_back_safely(self):
        self.assertEqual(services.parse_range("6"), 6)
        for bad in (None, "", "abc", "5", "-3", "999"):
            self.assertEqual(services.parse_range(bad), services.DEFAULT_RANGE)

    def test_report_totals_and_month_buckets(self):
        book = make_book(self.alice, title="Top", price="100.00", genre="Fiction")
        make_sale(book, 2, aware(2026, 9))     # 200
        make_sale(book, 3, aware(2026, 10))    # 300
        make_sale(book, 1, aware(2026, 10))    # 100
        report = services.sales_report(self.alice, 3, self.TODAY)
        self.assertEqual(report["revenue"], Decimal("600.00"))
        self.assertEqual(report["units"], 6)
        self.assertEqual(report["orders"], 3)
        self.assertEqual(report["average_order_value"], Decimal("200.00"))
        self.assertEqual([m["revenue"] for m in report["monthly"]], [Decimal("0.00"), Decimal("200.00"), Decimal("400.00")])
        self.assertEqual(report["change_percent"], 100.0)
        self.assertEqual(report["top_books"][0]["book__title"], "Top")
        self.assertEqual(report["genres"][0]["genre"], "Fiction")

    def test_unit_price_at_time_of_sale_is_used(self):
        book = make_book(self.alice, price="999.00")
        make_sale(book, 2, aware(2026, 10), unit_price="50.00")
        self.assertEqual(services.sales_report(self.alice, 3, self.TODAY)["revenue"], Decimal("100.00"))

    def test_cancelled_and_failed_orders_do_not_count_any_case(self):
        book = make_book(self.alice, price="100.00")
        for status in ("CANCELLED", "cancelled", "Canceled", "FAILED"):
            make_sale(book, 5, aware(2026, 10), status=status)
        make_sale(book, 1, aware(2026, 10), status="PENDING")
        report = services.sales_report(self.alice, 3, self.TODAY)
        self.assertEqual(report["revenue"], Decimal("100.00"))
        self.assertEqual(services.inventory_kpis(self.alice)["units_sold"], 1)

    def test_other_sellers_sales_never_leak(self):
        make_sale(make_book(self.bob, price="500.00"), 4, aware(2026, 10))
        report = services.sales_report(self.alice, 12, self.TODAY)
        self.assertEqual((report["revenue"], report["orders"], report["top_books"]), (Decimal("0.00"), 0, []))

    def test_sales_outside_range_excluded(self):
        book = make_book(self.alice, price="100.00")
        make_sale(book, 1, aware(2025, 1))
        self.assertEqual(services.sales_report(self.alice, 3, self.TODAY)["revenue"], Decimal("0.00"))

    def test_empty_report_has_no_division_errors(self):
        report = services.sales_report(self.alice, 12, self.TODAY)
        self.assertEqual(report["average_order_value"], Decimal("0.00"))
        self.assertIsNone(report["change_percent"])
        self.assertEqual(len(report["chart"]["bars"]), 12)

    def test_page_renders_with_chart_table_and_bad_range(self):
        make_sale(make_book(self.alice), 1, timezone.now())
        self.client.force_login(self.alice)
        response = self.client.get(reverse("seller:analytics"), {"months": "banana"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<svg")
        self.assertContains(response, "View the chart as a table")
        self.assertContains(response, "Top selling books")

    def test_page_with_no_sales_shows_message(self):
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("seller:analytics")), "have sold in this period")

    def test_csv_export_content_and_headers(self):
        make_sale(make_book(self.alice, price="100.00"), 2, timezone.now())
        self.client.force_login(self.alice)
        response = self.client.get(reverse("seller:analytics-export"), {"months": "3"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("seller-sales-3-months.csv", response["Content-Disposition"])
        lines = response.content.decode().strip().splitlines()
        self.assertEqual(lines[0], "Month,Revenue (INR),Units sold,Orders")
        self.assertEqual(len(lines), 4)

    def test_csv_formula_guard(self):
        self.assertEqual(services.csv_safe("=SUM(A1)"), "'=SUM(A1)")
        self.assertEqual(services.csv_safe("@cmd"), "'@cmd")
        self.assertEqual(services.csv_safe("Oct 2026"), "Oct 2026")


class NavigationTests(SellerTestCase):
    def test_seller_links_added_to_storefront_nav(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse("seller:dashboard"))
        self.assertContains(response, reverse("seller:analytics"))
        self.assertContains(response, 'class="skip-link"')
        self.assertContains(response, "<h1>Seller dashboard</h1>", html=True)
