from django.urls import path

from .views import BooksPageView

app_name = "storefront"

urlpatterns = [
    path("", BooksPageView.as_view(), name="books"),
]