from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from accounts.models import Address
from orders.models import Order

from .sms import normalize_phone, send_sms
from .tasks import send_order_confirmation_sms


@override_settings(SMS_BACKEND="notifications.sms.ConsoleSMSBackend", SMS_DEFAULT_COUNTRY_CODE="+91")
class SmsTests(TestCase):
    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("98765 43210"), "+919876543210")
        self.assertEqual(normalize_phone("09876543210"), "+919876543210")
        self.assertEqual(normalize_phone("919876543210"), "+919876543210")
        self.assertEqual(normalize_phone("+1 (555) 000-1111"), "+15550001111")
        self.assertEqual(normalize_phone(""), "")

    def test_console_backend_logs_the_message(self):
        with self.assertLogs("notifications.sms", level="INFO") as logs:
            sent = send_sms("9876543210", "Your order is placed")
        self.assertTrue(sent)
        self.assertIn("+919876543210", logs.output[0])
        self.assertIn("Your order is placed", logs.output[0])

    def test_empty_number_is_skipped(self):
        with self.assertLogs("notifications.sms", level="WARNING"):
            self.assertFalse(send_sms("", "hello"))

    @override_settings(
        SMS_BACKEND="notifications.sms.TwilioSMSBackend",
        TWILIO_ACCOUNT_SID="AC123",
        TWILIO_AUTH_TOKEN="secret",
        TWILIO_FROM_NUMBER="+15550001111",
    )
    @patch("notifications.sms.urlopen")
    def test_twilio_backend_posts_to_the_messages_api(self, urlopen):
        urlopen.return_value.__enter__.return_value.status = 201
        self.assertTrue(send_sms("9876543210", "hello"))

        request = urlopen.call_args.args[0]
        self.assertIn("/Accounts/AC123/Messages.json", request.full_url)
        self.assertIn(b"To=%2B919876543210", request.data)
        self.assertIn(b"Body=hello", request.data)


class OrderSmsTaskTests(TestCase):
    def make_order(self, phone):
        user = get_user_model().objects.create_user(
            username="reader", email="reader@example.com", password="Pass12345!"
        )
        address = Address.objects.create(
            user=user, recipient_name="Zia", line1="1 Road", city="Bengaluru",
            state="Karnataka", postal_code="560001", phone=phone,
        )
        return Order.objects.create(
            user=user, delivery_address=address,
            total_amount=Decimal("499.00"), status="PENDING",
        )

    @patch("notifications.tasks.send_sms")
    def test_sms_goes_to_the_delivery_address_phone(self, send_sms_mock):
        order = self.make_order("98765 43210")
        send_order_confirmation_sms(order.pk)
        send_sms_mock.assert_called_once()
        self.assertEqual(send_sms_mock.call_args.args[0], "98765 43210")
        self.assertIn(f"#{order.pk}", send_sms_mock.call_args.args[1])

    @patch("notifications.tasks.send_sms")
    def test_no_phone_number_means_no_sms(self, send_sms_mock):
        order = self.make_order("")
        send_order_confirmation_sms(order.pk)
        send_sms_mock.assert_not_called()