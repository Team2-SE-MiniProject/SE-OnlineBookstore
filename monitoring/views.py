import time

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse

from .middleware import REDIS_CLIENT

PROCESS_START_TIME = time.time()


def health_check(request):
    """Report application, database, and Redis health."""
    checks = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception:
        checks["database"] = "unhealthy"

    try:
        REDIS_CLIENT.ping()
        checks["redis"] = "healthy"
    except redis.RedisError:
        checks["redis"] = "unhealthy"

    checks["application"] = "healthy"
    checks["uptime_seconds"] = round(time.time() - PROCESS_START_TIME, 2)

    is_healthy = all(
        checks[service] == "healthy"
        for service in ("database", "redis", "application")
    )

    return JsonResponse(
        {
            "status": "healthy" if is_healthy else "unhealthy",
            "checks": checks,
        },
        status=200 if is_healthy else 503,
    )


def metrics(request):
    """Return application monitoring metrics from Redis."""
    try:
        total_checkouts = int(
            REDIS_CLIENT.get("monitoring:checkout:total") or 0
        )
        failed_checkouts = int(
            REDIS_CLIENT.get("monitoring:checkout:failures") or 0
        )
        api_requests = int(
            REDIS_CLIENT.get("monitoring:api:requests") or 0
        )
        total_response_time = float(
            REDIS_CLIENT.get("monitoring:api:response_time_total") or 0
        )

        failure_rate = (
            failed_checkouts / total_checkouts * 100
            if total_checkouts
            else 0
        )
        average_response_time = (
            total_response_time / api_requests
            if api_requests
            else 0
        )

        return JsonResponse(
            {
                "checkout": {
                    "total": total_checkouts,
                    "failures": failed_checkouts,
                    "failure_rate_percent": round(failure_rate, 2),
                },
                "api": {
                    "requests": api_requests,
                    "average_response_time_seconds": round(
                        average_response_time, 4
                    ),
                },
            }
        )

    except redis.RedisError:
        return JsonResponse(
            {"error": "Monitoring metrics are temporarily unavailable."},
            status=503,
        )
