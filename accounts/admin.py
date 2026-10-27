from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AccountLockout, Address, AuditLog

User = get_user_model()

# Names shown at the top of the admin pages (the admin dashboard, SRS BOOK-F-050 to 054).
admin.site.site_header = "Online Bookstore Admin"
admin.site.site_title = "Online Bookstore Admin"
admin.site.index_title = "Dashboard"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("recipient_name", "user", "city", "state", "postal_code")
    search_fields = ("recipient_name", "user__username", "city", "postal_code")


# ---- Users and roles ----
try:
    admin.site.unregister(User)  # replace Django's plain user screen with ours
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class BookstoreUserAdmin(DjangoUserAdmin):
    """User list with status filters and bulk actions. Roles are set with the Groups field."""

    list_display = (
        "username", "email", "groups_list", "is_active", "is_staff",
        "is_locked", "date_joined", "last_login",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email")
    actions = ["activate_users", "deactivate_users", "unlock_accounts"]

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("account_lockout")
            .prefetch_related("groups")
        )

    @admin.display(description="Groups")
    def groups_list(self, obj):
        return ", ".join(group.name for group in obj.groups.all()) or "-"

    @admin.display(boolean=True, description="Locked")
    def is_locked(self, obj):
        lockout = getattr(obj, "account_lockout", None)
        return bool(lockout and lockout.is_locked())

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        users = list(queryset.filter(is_active=False))
        for user in users:
            user.is_active = True
            user.save(update_fields=["is_active"])
            self.log_change(request, user, "Activated by admin action")
        self.message_user(request, f"Activated {len(users)} user(s).")

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        if queryset.filter(pk=request.user.pk).exists():
            self.message_user(
                request, "You cannot deactivate your own account.", level=messages.WARNING
            )
        users = list(queryset.filter(is_active=True).exclude(pk=request.user.pk))
        for user in users:
            user.is_active = False
            user.save(update_fields=["is_active"])
            self.log_change(request, user, "Deactivated by admin action")
        self.message_user(request, f"Deactivated {len(users)} user(s).")

    @admin.action(description="Unlock selected accounts (clear failed logins)")
    def unlock_accounts(self, request, queryset):
        count = 0
        for lockout in AccountLockout.objects.filter(user__in=queryset).select_related("user"):
            if lockout.failed_attempts or lockout.locked_until:
                lockout.failed_attempts = 0
                lockout.locked_until = None
                lockout.save()
                self.log_change(request, lockout.user, "Account unlocked by admin action")
                count += 1
        self.message_user(request, f"Unlocked {count} account(s).")


# ---- Logs (read only, SRS BOOK-SR-005) ----
class ReadOnlyAdmin(admin.ModelAdmin):
    """Nobody can add, edit or delete these records from the admin."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogEntry)
class AdminActionLogAdmin(ReadOnlyAdmin):
    """Every change made through the admin: who, when, what."""

    date_hierarchy = "action_time"
    list_display = ("action_time", "user", "content_type", "object_repr", "action", "details")
    list_filter = ("action_flag", "content_type", "user")
    search_fields = ("object_repr", "change_message", "user__username")

    @admin.display(description="Action")
    def action(self, obj):
        return obj.get_action_flag_display()

    @admin.display(description="Details")
    def details(self, obj):
        return obj.get_change_message()


@admin.register(AuditLog)
class SecurityEventLogAdmin(ReadOnlyAdmin):
    """Registrations, verifications and account lockouts."""

    date_hierarchy = "created_at"
    list_display = ("created_at", "event", "username", "details")
    list_filter = ("event",)
    search_fields = ("username", "details")
