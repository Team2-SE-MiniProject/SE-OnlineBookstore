"""URL configuration for the bookstore project."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/books/", include("catalog.urls")),
    path("api/books/", include("reviews.urls")),
    path("api/wishlist/", include("wishlist.urls")),
    path("api/cart/", include("cart.urls")),
    path("", include("storefront.urls")),
    path("api/auth/", include("accounts.api_urls")),
]
