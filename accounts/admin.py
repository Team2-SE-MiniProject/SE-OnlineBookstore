from django.contrib import admin

from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "user", "city", "state", "postal_code")
    search_fields = ("recipient_name", "user__username", "city", "postal_code")
