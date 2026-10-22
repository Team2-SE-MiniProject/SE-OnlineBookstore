import logging

from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    415: "unsupported_media_type",
    429: "too_many_requests",
}


def api_exception_handler(exc, context):
    """Return every API error as {code, message} (SAD 4.4)."""
    response = exception_handler(exc, context)

    if response is None:
        # Not an API error, so it is a real bug.
        if settings.DEBUG:
            return None  # let Django show its debug page while developing
        request = context.get("request")
        # Only method and path are logged: never the body, headers or query string.
        logger.error(
            "Unhandled error on %s %s",
            getattr(request, "method", "?"),
            getattr(request, "path", "?"),
            exc_info=exc,
        )
        return Response(
            {"code": "server_error", "message": "Something went wrong on our side."},
            status=500,
        )

    if isinstance(exc, ValidationError):
        code, message, details = "validation_error", "Invalid input.", response.data
    else:
        data = response.data
        code = CODES.get(response.status_code, "error")
        message = str(data.get("detail", "Request failed.")) if isinstance(data, dict) else "Request failed."
        details = None

    body = {"code": code, "message": message}
    if details is not None:
        body["details"] = details  # field-by-field errors for forms
    response.data = body
    return response