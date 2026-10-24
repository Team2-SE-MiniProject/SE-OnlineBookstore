from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self):
        from django.db.models.signals import post_migrate
        from .signals import create_role_groups

        post_migrate.connect(
            create_role_groups,
            sender=self,
            dispatch_uid="accounts.create_role_groups",
        )
