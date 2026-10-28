from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """
    Catalog moderation for admins and inventory management for sellers.
    A seller only sees and edits their own books, and any book they add belongs to them.
    """

    list_display = ("title", "author", "genre", "price", "stock", "isbn", "has_cover")
    list_editable = ("price", "stock")  # edit straight from the list
    search_fields = ("title", "author", "isbn", "genre")
    ordering = ("title",)
    list_per_page = 25
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_out_of_stock"]

    # ---- who sees what ----
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(seller=request.user)

    def get_list_display(self, request):
        columns = super().get_list_display(request)
        return (*columns, "seller") if request.user.is_superuser else columns

    def get_list_filter(self, request):
        return ("genre", "seller") if request.user.is_superuser else ("genre",)

    def get_exclude(self, request, obj=None):
        return None if request.user.is_superuser else ("seller",)

    def save_model(self, request, obj, form, change):
        if not change and not request.user.is_superuser:
            obj.seller = request.user  # a seller's new books always belong to them
        super().save_model(request, obj, form, change)

    # ---- columns and actions ----
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