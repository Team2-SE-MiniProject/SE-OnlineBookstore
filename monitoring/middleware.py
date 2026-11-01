import logging
import time

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

REDIS_CLIENT = redis.Redis.from_url(
    settings.CELERY_BROKER_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


class MonitoringMiddleware:
    """Collect lightweight application metrics using shared Redis counters."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.monotonic()

        response = self.get_response(request)

        duration = time.monotonic() - start_time
        path = request.path
        status_code = response.status_code

        try:
            if path.startswith("/api/"):
                REDIS_CLIENT.incr("monitoring:api:requests")
                REDIS_CLIENT.incrbyfloat(
                    "monitoring:api:response_time_total",
                    duration,
                )

            if path.rstrip("/") == "/api/orders/checkout":
                REDIS_CLIENT.incr("monitoring:checkout:total")

                if status_code >= 400:
                    REDIS_CLIENT.incr("monitoring:checkout:failures")

        except redis.RedisError:
            logger.warning("Unable to record monitoring metrics in Redis.")

        return response
