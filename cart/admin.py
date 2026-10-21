from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "is_active", "created_at", "updated_at")
    list_filter = ("is_active",)
    inlines = (CartItemInline,)
