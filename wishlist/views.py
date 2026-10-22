from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Book

from .models import WishlistItem


def error(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "message": message}, status=http_status)


def serialize_wishlist(user):
    items = []
    for item in WishlistItem.objects.filter(user=user).select_related("book"):
        book = item.book
        items.append(
            {
                "id": item.id,
                "added_at": item.created_at.isoformat(),
                "book": {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "price": str(book.price),
                    "cover": book.cover,
                    "stock": book.stock,
                    "in_stock": book.stock > 0,
                },
            }
        )
    return {"items": items, "total": len(items)}


class WishlistView(APIView):
    """GET /api/wishlist/ - list. POST /api/wishlist/ - add a book."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(serialize_wishlist(request.user))

    def post(self, request):
        raw = request.data.get("bookId")
        try:
            if isinstance(raw, bool):
                raise ValueError
            book_id = int(raw)
            if book_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return error("invalid_request", "bookId must be a positive integer.")

        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return error("book_not_found", "Book not found.", status.HTTP_404_NOT_FOUND)

        _, created = WishlistItem.objects.get_or_create(user=request.user, book=book)
        return Response(
            serialize_wishlist(request.user),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class WishlistItemView(APIView):
    """DELETE /api/wishlist/<book_id>/ - remove a book."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, book_id):
        deleted, _ = WishlistItem.objects.filter(
            user=request.user, book_id=book_id
        ).delete()
        if not deleted:
            return error(
                "item_not_found",
                "Book is not in your wishlist.",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(serialize_wishlist(request.user))
