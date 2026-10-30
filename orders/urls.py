from django.urls import path

from .views import (
    checkout,
    order_history,
    create_return_refund_request,
    list_return_refund_requests,
)

urlpatterns = [
    path("checkout", checkout, name="order-checkout"),
    path("history", order_history, name="order-history"),
    path(
        "<int:order_id>/return-refund",
        create_return_refund_request,
        name="create-return-refund-request",
    ),
    path(
        "return-refund-requests",
        list_return_refund_requests,
        name="list-return-refund-requests",
    ),
]
