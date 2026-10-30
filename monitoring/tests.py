import json
from unittest.mock import patch

import redis
from django.test import TestCase, RequestFactory

from .views import health_check, metrics


class MonitoringTests(TestCase):

    @patch("monitoring.views.REDIS_CLIENT.ping", return_value=True)
    def test_health_check_returns_healthy(self, mock_ping):
        response = health_check(RequestFactory().get("/health/"))
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "healthy")
        self.assertIn("uptime_seconds", data["checks"])

    @patch(
        "monitoring.views.REDIS_CLIENT.ping",
        side_effect=redis.ConnectionError("Redis unavailable"),
    )
    def test_health_check_returns_unhealthy_when_redis_fails(self, mock_ping):
        response = health_check(RequestFactory().get("/health/"))
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(data["status"], "unhealthy")

    @patch("monitoring.views.REDIS_CLIENT.get")
    def test_metrics_returns_expected_values(self, mock_get):
        values = {
            "monitoring:checkout:total": "10",
            "monitoring:checkout:failures": "2",
            "monitoring:api:requests": "20",
            "monitoring:api:response_time_total": "4.0",
        }
        mock_get.side_effect = lambda key: values.get(key)

        response = metrics(RequestFactory().get("/metrics/"))
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["checkout"]["failure_rate_percent"], 20.0)
        self.assertEqual(data["api"]["requests"], 20)
        self.assertEqual(data["api"]["average_response_time_seconds"], 0.2)

    @patch("monitoring.views.REDIS_CLIENT.get", return_value=None)
    def test_metrics_handles_empty_data(self, mock_get):
        response = metrics(RequestFactory().get("/metrics/"))
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["checkout"]["failure_rate_percent"], 0)
        self.assertEqual(data["api"]["average_response_time_seconds"], 0)
