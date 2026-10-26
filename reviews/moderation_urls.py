from django.urls import path

from .moderation import ModerationDetailView, ModerationListView

urlpatterns = [
    path("moderation/", ModerationListView.as_view(), name="review-moderation-list"),
    path(
        "moderation/<int:review_id>/",
        ModerationDetailView.as_view(),
        name="review-moderation-detail",
    ),
]
