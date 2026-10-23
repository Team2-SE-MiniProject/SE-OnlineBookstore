from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from orders.models import Order
from .tasks import send_order_confirmation_email, send_registration_email, enqueue_task_safely


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotificationTaskTests(TestCase):
    def test_registration_task_sends_verification_email(self):
        send_registration_email.apply(
            args=("reader", "reader@example.com", "https://example.com/verify/token")
        ).get()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["reader@example.com"])
        self.assertIn("https://example.com/verify/token", mail.outbox[0].body)

    def test_order_task_sends_confirmation_email(self):
        user = get_user_model().objects.create_user(
            username="reader", email="reader@example.com", password="StrongPass123!"
        )
        order = Order.objects.create(user=user, total_amount=Decimal("25.00"))
        send_order_confirmation_email.apply(args=(order.pk,)).get()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["reader@example.com"])
        self.assertIn(f"#{order.pk}", mail.outbox[0].subject)

    def test_enqueue_failure_is_swallowed(self):
        with patch("notifications.tasks.logger.exception") as log_exception:
            with patch.object(send_registration_email, "delay", side_effect=ConnectionError("broker down")):
                enqueue_task_safely(send_registration_email, "reader", "reader@example.com", "url")
        log_exception.assert_called_once()

    def test_sample_task_doubles_value(self):
        from .tasks import sample_task
        result = sample_task.apply(args=[5])
        self.assertEqual(result.get(), 10)
