from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from .permissions import IsAdminRole, IsBuyer, IsSeller
from .roles import assign_role


class RoleAssignmentTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="rbac_test_user",
            password="TestPassword123!",
        )

    def test_assign_each_supported_role(self):
        for role in ("buyer", "seller", "admin"):
            assign_role(self.user, role)
            self.assertTrue(self.user.groups.filter(name=role).exists())
            self.assertEqual(self.user.groups.count(), 1)

    def test_invalid_role_is_rejected(self):
        with self.assertRaises(ValueError):
            assign_role(self.user, "unknown")


class RolePermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="permission_user")
        self.factory = APIRequestFactory()
        self.view = APIView()

    def check_permission(self, permission, user=None):
        request = self.factory.get("/test/")
        if user is not None:
            force_authenticate(request, user=user)
        drf_request = self.view.initialize_request(request)
        return permission.has_permission(drf_request, self.view)

    def test_buyer_permission(self):
        assign_role(self.user, "buyer")
        self.assertTrue(self.check_permission(IsBuyer(), self.user))
        self.assertFalse(self.check_permission(IsSeller(), self.user))
        self.assertFalse(self.check_permission(IsAdminRole(), self.user))

    def test_seller_permission(self):
        assign_role(self.user, "seller")
        self.assertTrue(self.check_permission(IsSeller(), self.user))
        self.assertFalse(self.check_permission(IsBuyer(), self.user))
        self.assertFalse(self.check_permission(IsAdminRole(), self.user))

    def test_admin_permission(self):
        assign_role(self.user, "admin")
        self.assertTrue(self.check_permission(IsAdminRole(), self.user))
        self.assertFalse(self.check_permission(IsBuyer(), self.user))
        self.assertFalse(self.check_permission(IsSeller(), self.user))

    def test_unauthenticated_user_is_denied(self):
        self.assertFalse(self.check_permission(IsBuyer()))
        self.assertFalse(self.check_permission(IsSeller()))
        self.assertFalse(self.check_permission(IsAdminRole()))
