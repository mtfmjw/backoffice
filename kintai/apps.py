from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class KintaiConfig(AppConfig):
    name = "kintai"
    verbose_name = _("勤怠管理")

    def ready(self):
        from django.contrib.auth.models import User

        # Overrides the verbose_name of the built-in username field
        User._meta.get_field("username").verbose_name = "ログインID"
