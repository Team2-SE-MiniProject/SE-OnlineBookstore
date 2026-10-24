from django.urls import path

from . import views
from .address_api import AddressListCreateView

app_name = "storefront"

urlpatterns = [
    path("", views.BooksPageView.as_view(), name="books"),
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("register/", views.RegisterPageView.as_view(), name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("cart/", views.CartPageView.as_view(), name="cart"),
    path("checkout/", views.CheckoutPageView.as_view(), name="checkout"),
    path("api/addresses/", AddressListCreateView.as_view(), name="address-list"),
]