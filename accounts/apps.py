from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

# WHAT MAKES THE SIGNALS WORKS
    def ready(self):
        import accounts.signals
