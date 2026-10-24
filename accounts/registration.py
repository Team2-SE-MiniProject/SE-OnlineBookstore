import json
import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_GET, require_POST

from .models import AuditLog
from notifications.tasks import enqueue_task_safely, send_registration_email

logger = logging.getLogger(__name__)


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token tied to the account's active state, so it stops working once used."""

    key_salt = "accounts.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.is_active}{user.email}{timestamp}"


verification_token = EmailVerificationTokenGenerator()


def error(code, message, status):
    return JsonResponse({"code": code, "message": message}, status=status)


def read_payload(request):
    """Accept form data (like login) or a JSON body."""
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body or b"{}")
        except ValueError:
            return None
        return data if isinstance(data, dict) else None
    return request.POST


def get_text(data, key, strip=True):
    value = data.get(key, "")
    if not isinstance(value, str):
        return ""
    return value.strip() if strip else value


def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = verification_token.make_token(user)
    link = request.build_absolute_uri(reverse("account-verify", args=[uid, token]))
    # Queue only after the user transaction commits; a broker outage must not
    # undo registration or make the request fail.
    transaction.on_commit(
        lambda: enqueue_task_safely(
            send_registration_email, user.username, user.email, link
        )
    )


@require_POST
def register_view(request):
    data = read_payload(request)
    if data is None:
        return error(
            "invalid_request", "Body must be valid JSON or form data.", 400
        )

    username = get_text(data, "username")
    email = get_text(data, "email").lower()
    password = get_text(data, "password", strip=False)

    if not username or not email or not password:
        return error(
            "invalid_request", "Username, email and password are required.", 400
        )

    try:
        validate_email(email)
    except ValidationError:
        return error("invalid_email", "Enter a valid email address.", 400)

    User = get_user_model()

    candidate = User(username=username, email=email)
    try:
        candidate.full_clean(exclude=["password"], validate_unique=False)
    except ValidationError as exc:
        return error("invalid_username", " ".join(exc.messages), 400)

    if User.objects.filter(email__iexact=email).exists():
        return error("email_taken", "An account with this email already exists.", 409)
    if User.objects.filter(username__iexact=username).exists():
        return error("username_taken", "This username is already taken.", 409)

    try:
        validate_password(password, candidate)
    except ValidationError as exc:
        return error("weak_password", " ".join(exc.messages), 400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=password, is_active=False
            )
            send_verification_email(request, user)
            AuditLog.objects.create(
                event="USER_REGISTERED",
                username=username,
                details="Registered; waiting for email verification.",
            )
    except IntegrityError:
        return error("username_taken", "This username is already taken.", 409)
    except OSError:
        # The whole block rolled back, so the person can simply try again.
        logger.exception("Could not send verification email")
        return error(
            "email_failed",
            "Could not send the verification email. Please try again.",
            503,
        )

    return JsonResponse(
        {"message": "Registration successful. Check your email to verify your account."},
        status=201,
    )


@require_GET
def verify_view(request, uidb64, token):
    User = get_user_model()
    try:
        user = User.objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not verification_token.check_token(user, token):
        return error(
            "invalid_link", "This verification link is invalid or has expired.", 400
        )

    user.is_active = True
    user.save(update_fields=["is_active"])
    AuditLog.objects.create(
        event="EMAIL_VERIFIED",
        username=user.username,
        details="Email verified; account activated.",
    )
    return JsonResponse({"message": "Email verified. You can now log in."})
