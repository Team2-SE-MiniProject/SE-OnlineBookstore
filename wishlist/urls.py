from django.urls import path

from .views import WishlistItemView, WishlistView

urlpatterns = [
    path("", WishlistView.as_view(), name="wishlist"),
    path("<int:book_id>/", WishlistItemView.as_view(), name="wishlist-item"),
]
