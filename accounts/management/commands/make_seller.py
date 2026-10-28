from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

SELLER_GROUP = "seller"

# What a seller may do in the admin: manage their own books, and view (and fulfil)
# the orders that contain them. The scoping to "own" records is done in the admin classes.
SELLER_PERMISSIONS = [
    ("catalog", "add_book"),
    ("catalog", "change_book"),
    ("catalog", "view_book"),
    ("orders", "view_order"),
    ("orders", "view_orderitem"),
]


class Command(BaseCommand):
    help = "Make a user a seller: staff access, the 'seller' group and its permissions."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--claim-unowned-books",
            action="store_true",
            help="Make this seller the owner of every book that has no seller yet (demo data).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"No user called '{options['username']}'.")

        group, _ = Group.objects.get_or_create(name=SELLER_GROUP)
        for app_label, codename in SELLER_PERMISSIONS:
            group.permissions.add(
                Permission.objects.get(content_type__app_label=app_label, codename=codename)
            )

        user.is_staff = True  # needed to log in to /admin/
        user.save(update_fields=["is_staff"])
        user.groups.add(group)
        self.stdout.write(self.style.SUCCESS(f"{user.username} is now a seller."))

        if options["claim_unowned_books"]:
            from catalog.models import Book

            claimed = Book.objects.filter(seller__isnull=True).update(seller=user)
            self.stdout.write(self.style.SUCCESS(f"{claimed} book(s) assigned to {user.username}."))