from django.urls import path

from .token_views import me, token_login

# No trailing slashes, to match the API paths in the SAD (/api/auth/login).
urlpatterns = [
    path("login", token_login, name="api-auth-login"),
    path("me", me, name="api-auth-me"),
]