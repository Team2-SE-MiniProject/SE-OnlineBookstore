from rest_framework.permissions import BasePermission


class IsBuyer(BasePermission):
    """Allow users assigned to the buyer group."""

    message = "Buyer role required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name="buyer").exists()
        )


class IsSeller(BasePermission):
    """Allow users assigned to the seller group."""

    message = "Seller role required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name="seller").exists()
        )


class IsAdminRole(BasePermission):
    """Allow Django administrators or users in the admin group."""

    message = "Admin role required."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.groups.filter(name="admin").exists()
            )
        )
