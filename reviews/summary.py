from django.db.models import Avg, Count


def serialize_review(review):
    return {
        "id": review.id,
        "user": review.user.username,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
    }


def rating_stats(book):
    """Average and count over approved reviews only."""
    stats = book.reviews.filter(is_approved=True).aggregate(
        avg=Avg("rating"), count=Count("id")
    )
    avg = stats["avg"]
    average = round(float(avg), 1) if avg is not None else None
    return average, stats["count"]


def review_summary(book, limit=5):
    """Used by the book detail page."""
    average, count = rating_stats(book)
    latest = (
        book.reviews.filter(is_approved=True)
        .select_related("user")
        .order_by("-created_at", "-id")[:limit]
    )
    return {
        "average_rating": average,
        "count": count,
        "items": [serialize_review(r) for r in latest],
    }
