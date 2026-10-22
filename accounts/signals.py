from django.contrib.auth.models import Group


def create_role_groups(sender, **kwargs):
    if sender.name != "accounts":
        return

    for role in ("buyer", "seller", "admin"):
        Group.objects.get_or_create(name=role)
