from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import Address
from cart.models import Cart
from notifications.tasks import (
    enqueue_task_safely,
    send_order_confirmation_email,
    send_order_confirmation_sms,
)
from catalog.models import Book
from .models import Coupon, Order, OrderItem


@api_view(["POST"])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def checkout(request):
    """Validate a customer's cart and create a pending order.

    Payment processing is intentionally represented by a placeholder URL until
    the team integrates a real payment gateway.
    """
    if not getattr(request.user, "is_authenticated", False):
        return Response(
            {"code": "authentication_required", "message": "Authentication required."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    data = request.data
    if not isinstance(data, dict):
        return Response(
            {"code": "invalid_request", "message": "Request body must be a JSON object."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart_id = data.get("cartId")
    address_id = data.get("addressId")
    coupon_code = data.get("couponCode")

    if not cart_id or not address_id:
        return Response(
            {"code": "invalid_request", "message": "cartId and addressId are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cart_id = int(cart_id)
        address_id = int(address_id)
    except (TypeError, ValueError):
        return Response(
            {"code": "invalid_request", "message": "cartId and addressId must be integers."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        try:
            cart = Cart.objects.select_for_update().get(
                pk=cart_id, user=request.user, is_active=True
            )
        except Cart.DoesNotExist:
            return Response(
                {"code": "cart_not_found", "message": "Active cart not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            address = Address.objects.get(pk=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response(
                {"code": "address_not_found", "message": "Delivery address not found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        cart_items = list(cart.items.select_related("book").all())
        if not cart_items:
            return Response(
                {"code": "empty_cart", "message": "Cannot check out an empty cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lock the books while validating stock and creating the order.
        book_ids = [item.book_id for item in cart_items]
        locked_books = {
            book.pk: book
            for book in Book.objects.select_for_update().filter(pk__in=book_ids)
        }

        for item in cart_items:
            book = locked_books.get(item.book_id)
            if book is None or book.stock < item.quantity:
                return Response(
                    {
                        "code": "out_of_stock",
                        "message": f"Insufficient stock for book '{item.book.title}'.",
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        subtotal = sum(
            (locked_books[item.book_id].price * item.quantity for item in cart_items),
            Decimal("0.00"),
        )
        total = subtotal
        applied_coupon = None

        if coupon_code:
            try:
                applied_coupon = Coupon.objects.get(
                    code=str(coupon_code).strip().upper(), is_active=True
                )
            except Coupon.DoesNotExist:
                return Response(
                    {"code": "invalid_coupon", "message": "Coupon code is invalid or inactive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if applied_coupon.discount_percent < 0 or applied_coupon.discount_percent > 100:
                return Response(
                    {"code": "invalid_coupon", "message": "Coupon discount is not valid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            total = (
                subtotal * (Decimal("100.00") - applied_coupon.discount_percent) / Decimal("100.00")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        order = Order.objects.create(
            user=request.user,
            delivery_address=address,
            total_amount=total,
            status="PENDING",
        )
        transaction.on_commit(
            lambda order_id=order.pk: enqueue_task_safely(
                send_order_confirmation_email, order_id
            )
        )
        
        transaction.on_commit(
            lambda order_id=order.pk: enqueue_task_safely(
                send_order_confirmation_sms, order_id
            )
        )
        
        for item in cart_items:
            book = locked_books[item.book_id]
            OrderItem.objects.create(
                order=order,
                book=book,
                quantity=item.quantity,
                unit_price=book.price,
            )
            order.books.add(book)

        # Do not decrement stock at order creation: the design specifies that
        # stock is reduced after successful payment confirmation.
        payment_base = getattr(
            settings, "PAYMENT_CHECKOUT_BASE_URL", "https://example.com/mock-payment"
        ).rstrip("/")
        payment_url = f"{payment_base}/{order.pk}"

        response_data = {
            "orderId": order.pk,
            "status": order.status,
            "paymentUrl": payment_url,
            "totalAmount": str(order.total_amount),
        }
        if applied_coupon:
            response_data["couponCode"] = applied_coupon.code

        return Response(response_data, status=status.HTTP_201_CREATED)

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
