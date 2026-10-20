
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model, login
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AccountLockout, AuditLog

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


@require_POST
def login_view(request):
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")

    if not username or not password:
        return JsonResponse(
            {"error": "Username and password are required."},
            status=400,
        )

    User = get_user_model()
    user = User.objects.filter(username=username).first()

    # Authenticate even for unknown usernames to reduce timing differences.
    if user is None:
        authenticate(request, username=username, password=password)
        return JsonResponse(
            {"error": "Invalid username or password."},
            status=401,
        )

    with transaction.atomic():
        lockout, _ = AccountLockout.objects.get_or_create(user=user)
        lockout = AccountLockout.objects.select_for_update().get(pk=lockout.pk)

        now = timezone.now()

        if lockout.locked_until and lockout.locked_until > now:
            return JsonResponse(
                {
                    "error": "Account is locked. Try again after 15 minutes.",
                    "locked_until": lockout.locked_until.isoformat(),
                },
                status=423,
            )

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
            return JsonResponse(
                {"error": "Invalid username or password."},
                status=401,
            )

        lockout.failed_attempts = 0
        lockout.locked_until = None
        lockout.save()

        login(request, authenticated_user)

    return JsonResponse({"message": "Login successful."}, status=200)
