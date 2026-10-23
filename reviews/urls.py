from django.urls import path

from .views import ReviewDetailView, ReviewListView

urlpatterns = [
    path("<int:book_id>/reviews/", ReviewListView.as_view(), name="review-list"),
    path(
        "<int:book_id>/reviews/<int:review_id>/",
        ReviewDetailView.as_view(),
        name="review-detail",
    ),
]
