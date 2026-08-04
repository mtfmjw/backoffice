from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class KintaiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kintai'
    verbose_name = _('Kintai')

    def ready(self):
        import kintai.signals  # noqa: F401
