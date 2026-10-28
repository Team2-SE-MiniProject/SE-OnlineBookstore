from .models import AuditLog


def log_admin_action(user, action, details=""):
    """Record an administrative action for auditing."""
    if user is None or not user.is_authenticated:
        return None

    return AuditLog.objects.create(
        event="ADMIN_ACTION",
        user=user,
        username=str(user.get_username()),
        details=f"{action}: {details}".strip(),
    )
