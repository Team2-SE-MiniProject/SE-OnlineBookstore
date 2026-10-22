from django.contrib.auth.models import Group


VALID_ROLES = ("buyer", "seller", "admin")


def assign_role(user, role):
    """Assign one supported role to a user."""
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}")

    group, _ = Group.objects.get_or_create(name=role)
    user.groups.set([group])
    return group
