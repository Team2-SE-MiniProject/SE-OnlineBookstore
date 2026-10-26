from django.core.paginator import EmptyPage, Paginator
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AuditLog

from .models import Review

PAGE_SIZE = 20
STATES = ("hidden", "approved", "all")


def error(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    return Response({"code": code, "message": message}, status=http_status)


def parse_bool(raw):
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str) and raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    return None


def serialize_for_moderator(review):
    return {
        "id": review.id,
        "book": {"id": review.book_id, "title": review.book.title},
        "user": review.user.username,
        "rating": review.rating,
        "comment": review.comment,
        "is_approved": review.is_approved,
        "created_at": review.created_at.isoformat(),
        "moderated_at": review.moderated_at.isoformat() if review.moderated_at else None,
    }


class ModerationListView(APIView):
    """GET /api/reviews/moderation/?status=hidden|approved|all (staff only)."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        state = request.query_params.get("status", "hidden")
        if state not in STATES:
            return error("invalid_status", f"status must be one of: {', '.join(STATES)}.")

        try:
            page = int(request.query_params.get("page", 1))
            if page < 1:
                raise ValueError
        except ValueError:
            return error("invalid_page", "page must be a positive integer.")

        reviews = Review.objects.select_related("user", "book").order_by("-created_at", "-id")
        if state == "hidden":
            reviews = reviews.filter(is_approved=False)
        elif state == "approved":
            reviews = reviews.filter(is_approved=True)

        paginator = Paginator(reviews, PAGE_SIZE)
        try:
            page_reviews = list(paginator.page(page).object_list)
        except EmptyPage:
            page_reviews = []

        return Response(
            {
                "total": paginator.count,
                "page": page,
                "results": [serialize_for_moderator(r) for r in page_reviews],
            }
        )


class ModerationDetailView(APIView):
    """
    PATCH  /api/reviews/moderation/<id>/  body {"approved": true|false}
    DELETE /api/reviews/moderation/<id>/  (staff only)
    """

    permission_classes = [IsAdminUser]

    def get_review(self, review_id):
        return Review.objects.select_related("user", "book").filter(pk=review_id).first()

    def patch(self, request, review_id):
        review = self.get_review(review_id)
        if review is None:
            return error("review_not_found", "Review not found.", status.HTTP_404_NOT_FOUND)

        approved = parse_bool(request.data.get("approved"))
        if approved is None:
            return error("invalid_request", "approved must be true or false.")

        review.is_approved = approved
        review.moderated_by = request.user
        review.moderated_at = timezone.now()
        review.save()

        AuditLog.objects.create(
            event="REVIEW_APPROVED" if approved else "REVIEW_HIDDEN",
            username=request.user.username,
            details=f"Review {review.id} on book {review.book_id} by {review.user.username}.",
        )
        return Response({"review": serialize_for_moderator(review)})

    def delete(self, request, review_id):
        review = self.get_review(review_id)
        if review is None:
            return error("review_not_found", "Review not found.", status.HTTP_404_NOT_FOUND)

        AuditLog.objects.create(
            event="REVIEW_DELETED",
            username=request.user.username,
            details=f"Review {review.id} on book {review.book_id} by {review.user.username}.",
        )
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
