from django.urls import path

from .registration import register_view, verify_view
from .views import login_view

urlpatterns = [
    path("login/", login_view, name="account-login"),
    path("register/", register_view, name="account-register"),
    path("verify/<uidb64>/<token>/", verify_view, name="account-verify"),
]
