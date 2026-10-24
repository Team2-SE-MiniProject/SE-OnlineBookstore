from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

ALGORITHM = "HS256"


def get_role(user):
    """
    The role shown to API clients: admin, seller or buyer.
    Kept in one place so the RBAC story (BOOK-SR-004) can change it later.
    """
    if user.is_superuser:
        return "admin"
    if user.groups.filter(name="seller").exists():
        return "seller"
    return "buyer"


def create_token(user):
    now = timezone.now()
    lifetime = getattr(settings, "JWT_ACCESS_LIFETIME", timedelta(hours=1))
    payload = {
        "sub": str(user.pk),
        "role": get_role(user),
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


class JWTAuthentication(BaseAuthentication):
    """Accepts 'Authorization: Bearer <token>' on any API endpoint."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != self.keyword.lower().encode():
            return None  # no Bearer header: let the other authenticators try

        if len(header) != 2:
            raise exceptions.AuthenticationFailed("Invalid Authorization header.")

        try:
            payload = jwt.decode(header[1], settings.SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired.")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token.")

        user = get_user_model().objects.filter(pk=payload.get("sub"), is_active=True).first()
        if user is None:
            raise exceptions.AuthenticationFailed("User not found.")
        return (user, payload)

    def authenticate_header(self, request):
        return self.keyword