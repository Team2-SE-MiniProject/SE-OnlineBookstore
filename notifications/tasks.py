import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, retry_backoff=True)
def send_registration_email(self, username, email, verification_link):
    try:
        send_mail(
            subject="Verify your Online Bookstore account",
            message=(
                f"Hi {username},\n\n"
                "Thanks for registering. Open this link to verify your email "
                "and activate your account:\n"
                f"{verification_link}\n\n"
                "If you did not register, you can ignore this email."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Registration email failed")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, retry_backoff=True)
def send_order_confirmation_email(self, order_id):
    from orders.models import Order

    try:
        order = Order.objects.select_related("user").get(pk=order_id)
        if not order.user.email:
            logger.warning("Order %s has no customer email; confirmation skipped", order_id)
            return

        send_mail(
            subject=f"Order confirmation #{order.pk}",
            message=(
                f"Hi {order.user.username},\n\n"
                f"Your order #{order.pk} has been created.\n"
                f"Total: {order.total_amount}\n"
                f"Status: {order.status}\n"
                "Thank you for shopping with us."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[order.user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Order confirmation email failed for order %s", order_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, retry_backoff=True)
def sample_task(self, value):
    """Sample task to verify Celery task execution."""
    return value * 2


def enqueue_task_safely(task, *args):
    """Queue work without allowing a broker outage to fail the user's request."""
    try:
        task.delay(*args)
    except Exception:
        logger.exception("Could not enqueue notification task %s", task.name)
