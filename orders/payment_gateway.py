import os
from decimal import Decimal

import razorpay
from django.conf import settings


def create_payment_order(order):
    """Create a Razorpay order using configured test or live credentials."""
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "") or os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or os.getenv("RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret:
        raise RuntimeError("Razorpay credentials are not configured.")

    client = razorpay.Client(auth=(key_id, key_secret))
    amount_paise = int(
        (Decimal(str(order.total_amount)) * Decimal("100"))
    )

    return client.order.create(
        data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": str(order.pk),
        }
    )
