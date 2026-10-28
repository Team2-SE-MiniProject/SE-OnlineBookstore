from django.contrib import admin, messages

from . import fulfilment
from .models import Coupon, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("book", "quantity", "unit_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Order oversight and fulfilment. Status changes go through the actions below."""

    date_hierarchy = "created_at"
    list_display = ("id", "user", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at")
    list_select_related = ("user",)
    search_fields = ("=id", "user__username", "user__email")
    readonly_fields = ("status",)  # so every change is checked against the rules
    inlines = (OrderItemInline,)
    actions = ["mark_shipped", "mark_delivered", "mark_cancelled"]

    def has_add_permission(self, request):
        return False  # orders are created by checkout only

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
