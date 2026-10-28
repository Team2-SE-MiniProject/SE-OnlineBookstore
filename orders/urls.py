from django.urls import path

from .views import checkout, order_history

urlpatterns = [
    path("checkout", checkout, name="order-checkout"),
    path("history", order_history, name="order-history"),
]
