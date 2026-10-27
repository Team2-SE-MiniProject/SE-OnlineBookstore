"""Who counts as a seller.

A seller is any logged-in user in the "Seller" group (created by the app's data
migration). Superusers are treated as sellers too so the pages can be tried
without extra setup. Add a user to the group from the Django admin
(Users > pick the user > Groups > Seller).
"""

SELLER_GROUP = "Seller"


def is_seller(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=SELLER_GROUP).exists()
