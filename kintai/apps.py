from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class KintaiConfig(AppConfig):
    name = "kintai"
    verbose_name = _("勤怠管理")
