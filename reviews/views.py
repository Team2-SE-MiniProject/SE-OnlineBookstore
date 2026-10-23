from django.core.paginator import EmptyPage, Paginator
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Book

from .models import Review
from .summary import rating_stats, serialize_review

PAGE_SIZE = 20
MAX_COMMENT_LENGTH = 2000


def error(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "message": message}, status=http_status)


def parse_rating(raw):
    """A whole number from 1 to 5, or None."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, float) and not raw.is_integer():
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if 1 <= value <= 5 else None


def parse_comment(raw):
    """Trimmed text up to the limit, or None if invalid."""
    if raw is None:
        return ""
    if not isinstance(raw, str):
        return None
    raw = raw.strip()
    return raw if len(raw) <= MAX_COMMENT_LENGTH else None


def review_response(review, http_status):
    average, total = rating_stats(review.book)
    return Response(
        {
            "review": serialize_review(review),
            "average_rating": average,
            "total": total,
        },
        status=http_status,
    )


class ReviewListView(APIView):
    """
    GET  /api/books/<book_id>/reviews/ - ratings and reviews (public).
    POST /api/books/<book_id>/reviews/ - add your review (login required).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, book_id):
        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return error("book_not_found", "Book not found.", status.HTTP_404_NOT_FOUND)

        try:
            page = int(request.query_params.get("page", 1))
            if page < 1:
                raise ValueError
        except ValueError:
            return error("invalid_page", "page must be a positive integer.")

        reviews = book.reviews.select_related("user").order_by("-created_at", "-id")
        paginator = Paginator(reviews, PAGE_SIZE)
        try:
            page_reviews = list(paginator.page(page).object_list)
        except EmptyPage:
            page_reviews = []

        average, total = rating_stats(book)
        return Response(
            {
                "average_rating": average,
                "total": total,
                "page": page,
                "results": [serialize_review(r) for r in page_reviews],
            }
        )

    def post(self, request, book_id):
        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return error("book_not_found", "Book not found.", status.HTTP_404_NOT_FOUND)

        rating = parse_rating(request.data.get("rating"))
        if rating is None:
            return error("invalid_rating", "rating must be a whole number from 1 to 5.")

        comment = parse_comment(request.data.get("comment"))
        if comment is None:
            return error(
                "invalid_comment",
                f"comment must be text of at most {MAX_COMMENT_LENGTH} characters.",
            )

        duplicate = error(
            "already_reviewed",
            "You have already reviewed this book.",
            status.HTTP_409_CONFLICT,
        )
        if Review.objects.filter(user=request.user, book=book).exists():
            return duplicate

        try:
            with transaction.atomic():
                review = Review.objects.create(
                    user=request.user, book=book, rating=rating, comment=comment
                )
        except IntegrityError:
            return duplicate

        return review_response(review, status.HTTP_201_CREATED)


class ReviewDetailView(APIView):
    """
    PATCH  /api/books/<book_id>/reviews/<review_id>/ - edit your own review.
    DELETE /api/books/<book_id>/reviews/<review_id>/ - delete your own review.
    """

    permission_classes = [IsAuthenticated]

    def get_review(self, request, book_id, review_id):
        return (
            Review.objects.select_related("book", "user")
            .filter(pk=review_id, book_id=book_id, user=request.user)
            .first()
        )

    def patch(self, request, book_id, review_id):
        review = self.get_review(request, book_id, review_id)
        if review is None:
            return error(
                "review_not_found", "Review not found.", status.HTTP_404_NOT_FOUND
            )

        if "rating" not in request.data and "comment" not in request.data:
            return error("invalid_request", "Send a rating, a comment, or both.")

        if "rating" in request.data:
            rating = parse_rating(request.data.get("rating"))
            if rating is None:
                return error(
                    "invalid_rating", "rating must be a whole number from 1 to 5."
                )
            review.rating = rating

        if "comment" in request.data:
            comment = parse_comment(request.data.get("comment"))
            if comment is None:
                return error(
                    "invalid_comment",
                    f"comment must be text of at most {MAX_COMMENT_LENGTH} characters.",
                )
            review.comment = comment

        review.save()
        return review_response(review, status.HTTP_200_OK)

    def delete(self, request, book_id, review_id):
        review = self.get_review(request, book_id, review_id)
        if review is None:
            return error(
                "review_not_found", "Review not found.", status.HTTP_404_NOT_FOUND
            )

        book = review.book
        review.delete()
        average, total = rating_stats(book)
        return Response({"average_rating": average, "total": total})
