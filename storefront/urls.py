from django.urls import path

from . import views

app_name = "storefront"

urlpatterns = [
    path("", views.BooksPageView.as_view(), name="books"),
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cart/", views.CartPageView.as_view(), name="cart"),
]