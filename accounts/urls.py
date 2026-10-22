from django.urls import path

from .rbac_views import SellerManagementView
from .views import login_view

urlpatterns = [
    path("login/", login_view, name="account-login"),
    path(
        "seller-management/",
        SellerManagementView.as_view(),
        name="seller-management",
    ),
]
