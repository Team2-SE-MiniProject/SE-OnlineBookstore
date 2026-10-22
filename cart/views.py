from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Book

from .models import Cart, CartItem


def error(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "message": message}, status=http_status)


def get_active_cart(user):
    """Each user has one active cart; checkout reads the same one."""
    cart = Cart.objects.filter(user=user, is_active=True).first()
    if cart is None:
        cart = Cart.objects.create(user=user)
    return cart


def parse_positive_int(raw):
    if isinstance(raw, bool):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 1 else None


def serialize_cart(cart):
    items = []
    subtotal = Decimal("0.00")
    total_items = 0
    for item in cart.items.select_related("book").order_by("id"):
        line_total = item.book.price * item.quantity
        subtotal += line_total
        total_items += item.quantity
        items.append(
            {
                "id": item.id,
                "book": {
                    "id": item.book.id,
                    "title": item.book.title,
                    "author": item.book.author,
                    "price": str(item.book.price),
                    "cover": item.book.cover,
                    "stock": item.book.stock,
                },
                "quantity": item.quantity,
                "line_total": str(line_total),
            }
        )
    return {
        "id": cart.id,
        "items": items,
        "total_items": total_items,
        "subtotal": str(subtotal),
    }


class CartView(APIView):
    """GET /api/cart/ - the logged-in user's active cart with totals."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(serialize_cart(get_active_cart(request.user)))


class CartItemListView(APIView):
    """POST /api/cart/items/ - add a book (or increase its quantity)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        book_id = parse_positive_int(request.data.get("bookId"))
        if book_id is None:
            return error("invalid_request", "bookId must be a positive integer.")

        quantity = parse_positive_int(request.data.get("quantity", 1))
        if quantity is None:
            return error("invalid_quantity", "quantity must be a positive integer.")

        with transaction.atomic():
            try:
                book = Book.objects.select_for_update().get(pk=book_id)
            except Book.DoesNotExist:
                return error(
                    "book_not_found", "Book not found.", status.HTTP_404_NOT_FOUND
                )

            cart = get_active_cart(request.user)
            item = cart.items.filter(book=book).first()
            new_quantity = quantity + (item.quantity if item else 0)

            if new_quantity > book.stock:
                return error(
                    "insufficient_stock",
                    f"Only {book.stock} copies of this book are in stock.",
                )

            if item:
                item.quantity = new_quantity
                item.save()
            else:
                CartItem.objects.create(cart=cart, book=book, quantity=new_quantity)

        return Response(serialize_cart(cart), status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    """PATCH /api/cart/items/<id>/ - set quantity. DELETE - remove the item."""

    permission_classes = [IsAuthenticated]

    def get_item(self, request, item_id):
        return (
            CartItem.objects.select_related("book", "cart")
            .filter(pk=item_id, cart__user=request.user, cart__is_active=True)
            .first()
        )

    def patch(self, request, item_id):
        item = self.get_item(request, item_id)
        if item is None:
            return error(
                "item_not_found", "Cart item not found.", status.HTTP_404_NOT_FOUND
            )

        quantity = parse_positive_int(request.data.get("quantity"))
        if quantity is None:
            return error("invalid_quantity", "quantity must be a positive integer.")

        if quantity > item.book.stock:
            return error(
                "insufficient_stock",
                f"Only {item.book.stock} copies of this book are in stock.",
            )

        item.quantity = quantity
        item.save()
        return Response(serialize_cart(item.cart))

    def delete(self, request, item_id):
        item = self.get_item(request, item_id)
        if item is None:
            return error(
                "item_not_found", "Cart item not found.", status.HTTP_404_NOT_FOUND
            )

        cart = item.cart
        item.delete()
        return Response(serialize_cart(cart))
