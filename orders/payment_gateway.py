import hashlib
import hmac
import os
from decimal import Decimal

import razorpay
from django.conf import settings


def get_razorpay_key_id():
    return getattr(settings, "RAZORPAY_KEY_ID", "") or os.getenv("RAZORPAY_KEY_ID", "")


def get_razorpay_client():
    key_id = get_razorpay_key_id()
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or os.getenv("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        raise RuntimeError("Razorpay credentials are not configured.")
    return razorpay.Client(auth=(key_id, key_secret))


def create_payment_order(order):
    client = get_razorpay_client()
    amount_paise = int((Decimal(str(order.total_amount)) * Decimal("100")).quantize(Decimal("1")))
    return client.order.create(data={"amount": amount_paise, "currency": "INR", "receipt": str(order.pk)})


def verify_payment_signature(order_id, payment_id, signature):
    secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or os.getenv("RAZORPAY_KEY_SECRET", "")
    if not all((secret, order_id, payment_id, signature)):
        return False
    message = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body, signature):
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
