from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model, login
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AccountLockout, AuditLog

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

# Outcomes of authenticate_with_lockout()
OK, INVALID, LOCKED = "ok", "invalid", "locked"


def authenticate_with_lockout(request, username, password):
    """
    Check a username and password and apply the lockout rule (BOOK-F-003):
    5 consecutive failures lock the account for 15 minutes.

    Shared by the session login (/accounts/login/) and the JWT login
    (/api/auth/login), so both follow exactly the same rules.

    Returns (OK, user), (INVALID, None) or (LOCKED, locked_until).
    """
    User = get_user_model()
    user = User.objects.filter(username=username).first()

    # Authenticate even for unknown usernames to reduce timing differences.
    if user is None:
        authenticate(request, username=username, password=password)
        return INVALID, None

    with transaction.atomic():
        lockout, _ = AccountLockout.objects.get_or_create(user=user)
        lockout = AccountLockout.objects.select_for_update().get(pk=lockout.pk)

        now = timezone.now()

        if lockout.locked_until and lockout.locked_until > now:
            return LOCKED, lockout.locked_until

        # Clear an expired lock before checking the new attempt.
        if lockout.locked_until and lockout.locked_until <= now:
            lockout.failed_attempts = 0
            lockout.locked_until = None

        authenticated_user = authenticate(
            request,
            username=username,
            password=password,
        )

        if authenticated_user is None:
            lockout.failed_attempts += 1

            if lockout.failed_attempts >= MAX_FAILED_ATTEMPTS:
                lockout.locked_until = now + LOCKOUT_DURATION
                AuditLog.objects.create(
                    event="ACCOUNT_LOCKED",
                    username=username,
                    details=(
                        "Account locked for 15 minutes after "
                        "5 consecutive failed login attempts."
                    ),
                )

            lockout.save()
            return INVALID, None

        lockout.failed_attempts = 0
        lockout.locked_until = None
        lockout.save()
        return OK, authenticated_user


@require_POST
def login_view(request):
    """Session login used by the storefront pages."""
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    if not username or not password:
        return JsonResponse(
            {"error": "Username and password are required."},
            status=400,
        )

    outcome, result = authenticate_with_lockout(request, username, password)

    if outcome == LOCKED:
        return JsonResponse(
            {
                "error": "Account is locked. Try again after 15 minutes.",
                "locked_until": result.isoformat(),
            },
            status=423,
        )

    if outcome == INVALID:
        return JsonResponse(
            {"error": "Invalid username or password."},
            status=401,
        )

    login(request, result)
    return JsonResponse({"message": "Login successful."}, status=200)