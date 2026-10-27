from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """Catalog moderation: find, correct, hide from sale or remove books."""

    list_display = ("title", "author", "genre", "price", "stock", "isbn", "has_cover")
    list_editable = ("price", "stock")  # edit straight from the list
    list_filter = ("genre",)
    search_fields = ("title", "author", "isbn", "genre")
    ordering = ("title",)
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_out_of_stock"]

    @admin.display(boolean=True, description="Cover")
    def has_cover(self, obj):
        return bool(obj.cover)

    @admin.action(description="Mark selected books out of stock")
    def mark_out_of_stock(self, request, queryset):
        books = list(queryset)
        for book in books:
            book.stock = 0
            book.save(update_fields=["stock", "updated_at"])
            self.log_change(request, book, "Marked out of stock by admin action")
        self.message_user(request, f"Marked {len(books)} book(s) out of stock.")
