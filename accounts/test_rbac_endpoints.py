from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .roles import assign_role


class SellerManagementEndpointTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(username="buyer_user")
        self.seller = User.objects.create_user(username="seller_user")
        self.admin = User.objects.create_user(username="admin_user")
        assign_role(self.buyer, "buyer")
        assign_role(self.seller, "seller")
        assign_role(self.admin, "admin")
        self.client = APIClient()
        self.url = reverse("seller-management")

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_buyer_is_forbidden(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_seller_is_allowed(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_admin_is_allowed(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
