from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .fulfilment import InvalidTransition, can_transition, change_status
from .models import Order


class TransitionRuleTests(SimpleTestCase):
    def test_orders_move_forward(self):
        self.assertTrue(can_transition("PENDING", "PAID"))
        self.assertTrue(can_transition("PAID", "SHIPPED"))
        self.assertTrue(can_transition("SHIPPED", "DELIVERED"))
        self.assertTrue(can_transition("PENDING", "CANCELLED"))

    def test_finished_orders_cannot_move(self):
        self.assertFalse(can_transition("DELIVERED", "SHIPPED"))
        self.assertFalse(can_transition("DELIVERED", "CANCELLED"))
        self.assertFalse(can_transition("CANCELLED", "PENDING"))

    def test_shipped_orders_cannot_be_cancelled(self):
        self.assertFalse(can_transition("SHIPPED", "CANCELLED"))

    def test_unknown_status_is_rejected(self):
        self.assertFalse(can_transition("PENDING", "LOST"))

    def test_old_lowercase_status_is_understood(self):
        self.assertTrue(can_transition("pending", "shipped"))


class FulfilmentTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin_user = User.objects.create_superuser(
            username="boss", email="boss@example.com", password="Pass12345!"
        )
        cls.customer = User.objects.create_user(
            username="reader", email="reader@example.com", password="Pass12345!"
        )

    def make_order(self, status="PENDING"):
        return Order.objects.create(user=self.customer, total_amount="100.00", status=status)


class ChangeStatusTests(FulfilmentTestCase):
    def test_valid_move_is_saved(self):
        order = self.make_order("PAID")
        change_status(order, "SHIPPED")
        order.refresh_from_db()
        self.assertEqual(order.status, "SHIPPED")

    def test_invalid_move_raises_and_changes_nothing(self):
        order = self.make_order("DELIVERED")
        with self.assertRaises(InvalidTransition):
            change_status(order, "SHIPPED")
        order.refresh_from_db()
        self.assertEqual(order.status, "DELIVERED")

    def test_lowercase_order_can_be_moved(self):
        order = self.make_order("pending")
        change_status(order, "SHIPPED")
        order.refresh_from_db()
        self.assertEqual(order.status, "SHIPPED")


class OrderAdminActionTests(FulfilmentTestCase):
    def setUp(self):
        self.client.force_login(self.admin_user)
        self.url = reverse("admin:orders_order_changelist")

    def run_action(self, action, *orders):
        return self.client.post(
            self.url, {"action": action, "_selected_action": [o.pk for o in orders]}
        )

    def test_mark_shipped(self):
        order = self.make_order("PAID")
        self.run_action("mark_shipped", order)
        order.refresh_from_db()
        self.assertEqual(order.status, "SHIPPED")

    def test_delivered_order_cannot_be_shipped_again(self):
        order = self.make_order("DELIVERED")
        self.run_action("mark_shipped", order)
        order.refresh_from_db()
        self.assertEqual(order.status, "DELIVERED")

    def test_shipped_order_cannot_be_cancelled(self):
        order = self.make_order("SHIPPED")
        self.run_action("mark_cancelled", order)
        order.refresh_from_db()
        self.assertEqual(order.status, "SHIPPED")

    def test_valid_orders_in_a_mixed_selection_still_move(self):
        good = self.make_order("PAID")
        bad = self.make_order("CANCELLED")
        self.run_action("mark_shipped", good, bad)
        good.refresh_from_db()
        bad.refresh_from_db()
        self.assertEqual(good.status, "SHIPPED")
        self.assertEqual(bad.status, "CANCELLED")

    def test_status_change_is_written_to_the_admin_log(self):
        order = self.make_order("PAID")
        self.run_action("mark_shipped", order)
        self.assertTrue(
            LogEntry.objects.filter(user=self.admin_user, object_id=str(order.pk)).exists()
        )

    def test_orders_cannot_be_added_from_the_admin(self):
        self.assertEqual(self.client.get(reverse("admin:orders_order_add")).status_code, 403)