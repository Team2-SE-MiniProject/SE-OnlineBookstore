"""Order statuses and the moves allowed between them (SRS BOOK-F-040 to 044)."""

PENDING = "PENDING"      # created at checkout, waiting for payment
PAID = "PAID"            # payment confirmed
SHIPPED = "SHIPPED"
DELIVERED = "DELIVERED"
CANCELLED = "CANCELLED"

ALL_STATUSES = (PENDING, PAID, SHIPPED, DELIVERED, CANCELLED)

# From each status, the statuses an order may move to next.
# PENDING may ship directly while online payment is not connected yet.
# Remove SHIPPED from that set when the payment gateway story goes live.
TRANSITIONS = {
    PENDING: {PAID, SHIPPED, CANCELLED},
    PAID: {SHIPPED, CANCELLED},
    SHIPPED: {DELIVERED},
    DELIVERED: set(),
    CANCELLED: set(),
}


class InvalidTransition(ValueError):
    """Raised when an order cannot move to the requested status."""


def normalize(status):
    """Older rows may be lowercase ("pending"), so compare in capitals."""
    return (status or "").strip().upper()


def can_transition(current, new):
    return normalize(new) in TRANSITIONS.get(normalize(current), set())


def change_status(order, new_status):
    """Move an order to a new status if the rules allow it, otherwise raise InvalidTransition."""
    current = normalize(order.status)
    new = normalize(new_status)

    if new not in ALL_STATUSES:
        raise InvalidTransition(f"'{new_status}' is not a valid status.")
    if not can_transition(current, new):
        raise InvalidTransition(f"Order {order.pk} cannot move from {current} to {new}.")

    order.status = new
    order.save(update_fields=["status"])
    return order