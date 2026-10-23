import os
from unittest import skipUnless

from celery.contrib.testing.worker import start_worker
from django.test import SimpleTestCase

from bookstore.celery import app as celery_app
from notifications.tasks import sample_task


@skipUnless(os.getenv("CI") == "true", "Requires the Redis service in CI")
class CeleryRedisWorkerTests(SimpleTestCase):
    def test_sample_task_runs_through_redis_worker(self):
        celery_app.conf.update(
            broker_url=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
            task_always_eager=False,
        )

        with start_worker(
            celery_app,
            pool="solo",
            concurrency=1,
            perform_ping_check=False,
        ):
            result = sample_task.delay(5)
            self.assertEqual(result.get(timeout=15), 10)
