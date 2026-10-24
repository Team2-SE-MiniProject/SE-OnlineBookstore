from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .authentication import create_token, get_role
from .views import INVALID, LOCKED, authenticate_with_lockout


@api_view(["POST"])
@authentication_classes([])  # login itself needs no existing session or token
@permission_classes([AllowAny])
def token_login(request):
    """
    POST /api/auth/login  (SAD 4.3)
    Body: {"email": ..., "password": ...} (a "username" works too).
    Returns {status, token, role}; 401 for bad credentials, 423 when locked.
    """
    data = request.data if hasattr(request.data, "get") else {}
    identifier = str(data.get("email") or data.get("username") or "").strip()
    password = str(data.get("password") or "")

    if not identifier or not password:
        return Response(
            {"code": "invalid_request", "message": "email (or username) and password are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Accounts are keyed by username, so turn an email into its username first.
    user = None
    if "@" in identifier:
        user = get_user_model().objects.filter(email__iexact=identifier).first()
    username = user.get_username() if user else identifier

    outcome, result = authenticate_with_lockout(request, username, password)

    if outcome == LOCKED:
        return Response(
            {
                "code": "account_locked",
                "message": "Account is locked. Try again after 15 minutes.",
                "locked_until": result.isoformat(),
            },
            status=status.HTTP_423_LOCKED,
        )

    if outcome == INVALID:
        return Response(
            {"code": "invalid_credentials", "message": "Invalid credentials."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response({"status": "success", "token": create_token(result), "role": get_role(result)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """GET /api/auth/me - who the current session or token belongs to."""
    user = request.user
    return Response(
        {
            "id": user.pk,
            "username": user.get_username(),
            "email": user.email,
            "role": get_role(user),
        }
    )