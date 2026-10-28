from django.contrib import admin, messages

from . import fulfilment
from .models import Coupon, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("book", "quantity", "unit_price")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(book__seller=request.user)  # sellers see only their own lines


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Order oversight and fulfilment.
    Admins see every order. A seller sees only orders that contain their books, with the
    address to ship to, and can mark them shipped or delivered (not cancel them).
    Status changes go through the actions below, which check the rules in fulfilment.py.
    """

    date_hierarchy = "created_at"
    list_display = ("id", "user", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at")
    list_select_related = ("user",)
    search_fields = ("=id", "user__username", "user__email")
    readonly_fields = ("status",)
    inlines = (OrderItemInline,)
    actions = ["mark_shipped", "mark_delivered", "mark_cancelled"]

    seller_fields = ("user", "shipping_address", "status", "created_at")

    # ---- who sees what ----
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(items__book__seller=request.user).distinct()

    def get_list_display(self, request):
        if request.user.is_superuser:
            return super().get_list_display(request)
        return ("id", "user", "status", "created_at")

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_fields(request, obj)
        return self.seller_fields

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_readonly_fields(request, obj)
        return self.seller_fields

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            actions.pop("mark_cancelled", None)  # cancelling is for admins
        return actions

    def has_add_permission(self, request):
        return False  # orders are created by checkout only

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="Ship to")
    def shipping_address(self, obj):
        address = obj.delivery_address
        if address is None:
            return "-"
        parts = [
            address.recipient_name,
            address.line1,
            address.line2,
            f"{address.city}, {address.state} {address.postal_code}",
            address.country,
            address.phone,
        ]
        return ", ".join(part for part in parts if part)

    # ---- fulfilment actions ----
    def _move(self, request, queryset, new_status):
        moved = 0
        problems = []
        for order in queryset:
            try:
                fulfilment.change_status(order, new_status)
            except fulfilment.InvalidTransition as exc:
                problems.append(str(exc))
                continue
            self.log_change(request, order, f"Status changed to {new_status} by admin action")
            moved += 1

        if moved:
            self.message_user(request, f"{moved} order(s) marked {new_status.lower()}.")
        for problem in problems[:5]:
            self.message_user(request, problem, level=messages.WARNING)
        if len(problems) > 5:
            self.message_user(
                request, f"{len(problems) - 5} more order(s) could not be changed.",
                level=messages.WARNING,
            )

    @admin.action(description="Mark selected orders as shipped")
    def mark_shipped(self, request, queryset):
        self._move(request, queryset, fulfilment.SHIPPED)

    @admin.action(description="Mark selected orders as delivered")
    def mark_delivered(self, request, queryset):
        self._move(request, queryset, fulfilment.DELIVERED)

    @admin.action(description="Cancel selected orders")
    def mark_cancelled(self, request, queryset):
        self._move(request, queryset, fulfilment.CANCELLED)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_percent", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code",)