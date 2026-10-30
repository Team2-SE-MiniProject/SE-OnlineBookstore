from django.contrib import admin
from django.utils import timezone

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Review moderation. Hidden reviews (is_approved off) stay in the database but are
    not shown on the book page or counted in its rating. Delete is also in the actions menu.
    """

    date_hierarchy = "created_at"
    list_display = ("book", "user", "rating", "short_comment", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    list_select_related = ("book", "user")
    search_fields = ("book__title", "user__username", "comment")
    readonly_fields = ("created_at",)
    actions = ["hide_reviews", "approve_reviews"]

    @admin.display(description="Comment")
    def short_comment(self, obj):
        text = obj.comment or ""
        return text if len(text) <= 60 else text[:60] + "…"

    def _moderate(self, request, queryset, approved):
        """Set is_approved, and fill the moderation fields too when the model has them."""
        field_names = {field.name for field in Review._meta.get_fields()}
        reviews = list(queryset)
        for review in reviews:
            review.is_approved = approved
            changed = ["is_approved"]
            if "moderated_at" in field_names:
                review.moderated_at = timezone.now()
                changed.append("moderated_at")
            if "moderated_by" in field_names:
                review.moderated_by = request.user
                changed.append("moderated_by")
            review.save(update_fields=changed)
            self.log_change(
                request, review, "Approved by admin action" if approved else "Hidden by admin action"
            )
        return len(reviews)

    @admin.action(description="Hide selected reviews (not approved)")
    def hide_reviews(self, request, queryset):
        count = self._moderate(request, queryset, approved=False)
        self.message_user(request, f"Hid {count} review(s).")

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        count = self._moderate(request, queryset, approved=True)
        self.message_user(request, f"Approved {count} review(s).")