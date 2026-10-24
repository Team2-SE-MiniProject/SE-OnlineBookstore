from django.urls import path

from .rbac_views import SellerManagementView
from .registration import register_view, verify_view
from .views import login_view

urlpatterns = [
    path("login/", login_view, name="account-login"),
    path(
        "seller-management/",
        SellerManagementView.as_view(),
        name="seller-management",
    ),
    path("register/", register_view, name="account-register"),
    path("verify/<uidb64>/<token>/", verify_view, name="account-verify"),
]
