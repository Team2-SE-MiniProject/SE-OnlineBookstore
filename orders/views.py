from decimal import Decimal, ROUND_HALF_UP
import json

from django.conf import settings
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Address
from cart.models import Cart
from notifications.tasks import (
    enqueue_task_safely,
    send_order_confirmation_email,
    send_order_confirmation_sms,
)
from catalog.models import Book
from . import fulfilment
from .models import Coupon, Order, OrderItem, ReturnRefundRequest
from .payment_gateway import (
    create_payment_order, get_razorpay_client, get_razorpay_key_id,
    verify_payment_signature, verify_webhook_signature,
)

@api_view(["POST"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def checkout(request):
    """Create an order and a Razorpay order; stock changes only after payment."""
    data = request.data
    if not isinstance(data, dict):
        return Response({"code": "invalid_request", "message": "Request body must be a JSON object."}, status=status.HTTP_400_BAD_REQUEST)

    cart_id, address_id = data.get("cartId"), data.get("addressId")
    coupon_code = data.get("couponCode")
    if not cart_id or not address_id:
        return Response({"code": "invalid_request", "message": "cartId and addressId are required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        cart_id, address_id = int(cart_id), int(address_id)
    except (TypeError, ValueError):
        return Response({"code": "invalid_request", "message": "cartId and addressId must be integers."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        try:
            cart = Cart.objects.select_for_update().get(pk=cart_id, user=request.user, is_active=True)
        except Cart.DoesNotExist:
            return Response({"code": "cart_not_found", "message": "Active cart not found for this user."}, status=status.HTTP_404_NOT_FOUND)
        try:
            address = Address.objects.get(pk=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({"code": "address_not_found", "message": "Delivery address not found for this user."}, status=status.HTTP_404_NOT_FOUND)

        cart_items = list(cart.items.select_related("book").all())
        if not cart_items:
            return Response({"code": "empty_cart", "message": "Cannot check out an empty cart."}, status=status.HTTP_400_BAD_REQUEST)
        book_ids = [item.book_id for item in cart_items]
        locked_books = {book.pk: book for book in Book.objects.select_for_update().filter(pk__in=book_ids)}
        for item in cart_items:
            book = locked_books.get(item.book_id)
            if book is None or book.stock < item.quantity:
                return Response({"code": "out_of_stock", "message": f"Insufficient stock for book '{item.book.title}'."}, status=status.HTTP_409_CONFLICT)

        subtotal = sum((locked_books[item.book_id].price * item.quantity for item in cart_items), Decimal("0.00"))
        total, applied_coupon = subtotal, None
        if coupon_code:
            try:
                applied_coupon = Coupon.objects.get(code=str(coupon_code).strip().upper(), is_active=True)
            except Coupon.DoesNotExist:
                return Response({"code": "invalid_coupon", "message": "Coupon code is invalid or inactive."}, status=status.HTTP_400_BAD_REQUEST)
            if applied_coupon.discount_percent < 0 or applied_coupon.discount_percent > 100:
                return Response({"code": "invalid_coupon", "message": "Coupon discount is not valid."}, status=status.HTTP_400_BAD_REQUEST)
            total = (subtotal * (Decimal("100.00") - applied_coupon.discount_percent) / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        order = Order.objects.create(user=request.user, delivery_address=address, total_amount=total, status=fulfilment.PENDING)
        for item in cart_items:
            book = locked_books[item.book_id]
            OrderItem.objects.create(order=order, book=book, quantity=item.quantity, unit_price=book.price)
            order.books.add(book)

        try:
            gateway_order = create_payment_order(order)
            gateway_order_id = gateway_order.get("id")
            if not gateway_order_id:
                raise RuntimeError("Razorpay did not return an order ID.")
            order.razorpay_order_id = gateway_order_id
            order.save(update_fields=["razorpay_order_id"])
        except Exception:
            # Roll back the order and its items instead of leaving an unpaid orphan.
            transaction.set_rollback(True)
            return Response({"code": "payment_gateway_unavailable", "message": "Could not start payment. Please try again."}, status=status.HTTP_502_BAD_GATEWAY)

        response_data = {
            "orderId": order.pk,
            "status": order.status,
            "razorpayOrderId": order.razorpay_order_id,
            "razorpayKeyId": get_razorpay_key_id(),
            "amount": int((order.total_amount * Decimal("100")).quantize(Decimal("1"))),
            "currency": "INR",
            "totalAmount": str(order.total_amount),
        }
        # Kept for compatibility with existing API consumers; frontend should open Razorpay Checkout
        # using razorpayKeyId, razorpayOrderId, amount, and currency.
        response_data["paymentUrl"] = "razorpay://checkout/" + order.razorpay_order_id
        if applied_coupon:
            response_data["couponCode"] = applied_coupon.code
        return Response(response_data, status=status.HTTP_201_CREATED)


def _mark_order_paid(order_id, razorpay_order_id, payment_id, amount_paise=None, currency="INR"):
    """Idempotently confirm payment and decrement inventory exactly once."""
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(pk=order_id)
        except Order.DoesNotExist:
            return False, "order_not_found"
        if order.status == fulfilment.PAID:
            return True, "already_paid"
        if order.status != fulfilment.PENDING or order.razorpay_order_id != razorpay_order_id:
            return False, "order_mismatch"
        expected_amount = int((order.total_amount * Decimal("100")).quantize(Decimal("1")))
        if currency != "INR" or (amount_paise is not None and int(amount_paise) != expected_amount):
            return False, "amount_mismatch"
        items = list(order.items.select_related("book").all())
        books = {b.pk: b for b in Book.objects.select_for_update().filter(pk__in=[i.book_id for i in items])}
        for item in items:
            book = books.get(item.book_id)
            if book is None or book.stock < item.quantity:
                return False, "out_of_stock"
        for item in items:
            book = books[item.book_id]
            book.stock -= item.quantity
            book.save(update_fields=["stock"])
        order.status = fulfilment.PAID
        order.razorpay_payment_id = payment_id
        order.save(update_fields=["status", "razorpay_payment_id"])
        transaction.on_commit(lambda oid=order.pk: enqueue_task_safely(send_order_confirmation_email, oid))
        transaction.on_commit(lambda oid=order.pk: enqueue_task_safely(send_order_confirmation_sms, oid))
        return True, "paid"


@api_view(["POST"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def verify_payment(request, order_id):
    """Verify Razorpay's checkout signature and confirm captured payment."""
    try:
        order = Order.objects.get(pk=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({"message": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    order_id_from_client = request.data.get("razorpay_order_id")
    payment_id = request.data.get("razorpay_payment_id")
    signature = request.data.get("razorpay_signature")
    if order_id_from_client != order.razorpay_order_id or not verify_payment_signature(order_id_from_client, payment_id, signature):
        return Response({"message": "Invalid payment signature."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        payment = get_razorpay_client().payment.fetch(payment_id)
    except Exception:
        return Response({"message": "Could not verify payment with Razorpay."}, status=status.HTTP_502_BAD_GATEWAY)
    if payment.get("status") != "captured" or payment.get("order_id") != order.razorpay_order_id:
        return Response({"message": "Payment has not been captured for this order."}, status=status.HTTP_400_BAD_REQUEST)
    ok, reason = _mark_order_paid(order.pk, order.razorpay_order_id, payment_id, payment.get("amount"), payment.get("currency", "INR"))
    if not ok:
        code = status.HTTP_409_CONFLICT if reason in ("out_of_stock", "order_mismatch") else status.HTTP_400_BAD_REQUEST
        return Response({"message": "Payment could not be applied to this order.", "code": reason}, status=code)
    return Response({"orderId": order.pk, "status": fulfilment.PAID, "paymentId": payment_id}, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@csrf_exempt
def razorpay_webhook(request):
    """Handle Razorpay payment.captured webhook; verify the raw-body signature."""
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(request.body, signature):
        return Response({"message": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        event = json.loads(request.body.decode("utf-8"))
        if event.get("event") != "payment.captured":
            return Response({"received": True}, status=status.HTTP_200_OK)
        payment = event["payload"]["payment"]["entity"]
        gateway_order_id = payment.get("order_id")
        payment_id = payment.get("id")
        order = Order.objects.get(razorpay_order_id=gateway_order_id)
    except (ValueError, KeyError, TypeError, Order.DoesNotExist):
        return Response({"message": "Invalid webhook payload or unknown order."}, status=status.HTTP_400_BAD_REQUEST)
    ok, reason = _mark_order_paid(order.pk, gateway_order_id, payment_id, payment.get("amount"), payment.get("currency", "INR"))
    if not ok:
        code = status.HTTP_409_CONFLICT if reason == "out_of_stock" else status.HTTP_400_BAD_REQUEST
        return Response({"message": "Webhook payment could not be applied.", "code": reason}, status=code)
    return Response({"received": True, "orderId": order.pk, "status": fulfilment.PAID}, status=status.HTTP_200_OK)

@api_view(["GET"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def order_history(request):
    """Return the authenticated buyer's order history."""
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items__book")
        .order_by("-created_at")
    )

    data = []
    for order in orders:
        data.append(
            {
                "orderId": order.pk,
                "status": order.status,
                "totalAmount": str(order.total_amount),
                "createdAt": order.created_at.isoformat(),
                "items": [
                    {
                        "bookId": item.book_id,
                        "title": item.book.title,
                        "quantity": item.quantity,
                        "unitPrice": str(item.unit_price),
                    }
                    for item in order.items.all()
                ],
            }
        )

    return Response(data, status=status.HTTP_200_OK)

@api_view(["POST"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def create_return_refund_request(request, order_id):
    """Allow a buyer to request a return/refund for their delivered order."""
    reason = request.data.get("reason", "")
    if not isinstance(reason, str) or not reason.strip():
        return Response(
            {"message": "A reason is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order = Order.objects.get(pk=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"message": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if fulfilment.normalize(order.status) != fulfilment.DELIVERED:
        return Response(
            {"message": "Return/refund requests are only allowed for delivered orders."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing_request = ReturnRefundRequest.objects.filter(order=order).exists()
    if existing_request:
        return Response(
            {"message": "A return/refund request already exists for this order."},
            status=status.HTTP_409_CONFLICT,
        )

    refund_request = ReturnRefundRequest.objects.create(
        order=order,
        requested_by=request.user,
        reason=reason.strip(),
    )

    return Response(
        {
            "id": refund_request.pk,
            "orderId": order.pk,
            "reason": refund_request.reason,
            "status": refund_request.status,
            "createdAt": refund_request.created_at.isoformat(),
        },
        status=status.HTTP_201_CREATED,
    )

@api_view(["GET"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def list_return_refund_requests(request):
    """List return/refund requests visible to the authenticated user."""
    requests = ReturnRefundRequest.objects.select_related(
        "order", "requested_by", "order__user"
    ).prefetch_related("order__items__book")

    if request.user.is_superuser or request.user.groups.filter(name="admin").exists():
        pass
    elif request.user.groups.filter(name="seller").exists():
        requests = requests.filter(order__items__book__seller=request.user).distinct()
    else:
        requests = requests.filter(order__user=request.user)

    data = [
        {
            "id": refund_request.pk,
            "orderId": refund_request.order_id,
            "buyer": refund_request.order.user.username,
            "reason": refund_request.reason,
            "status": refund_request.status,
            "createdAt": refund_request.created_at.isoformat(),
            "updatedAt": refund_request.updated_at.isoformat(),
        }
        for refund_request in requests.order_by("-created_at")
    ]

    return Response(data, status=status.HTTP_200_OK)