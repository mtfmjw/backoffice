from django.db import models
from django.utils.translation import gettext_lazy as _


class Prefecture(models.Model):
    """都道府県マスタ"""

    code = models.CharField(_("Prefecture Code"), max_length=2, unique=True)  # 都道府県コード
    name = models.CharField(_("Prefecture Name"), max_length=100)  # 都道府県名

    class Meta:  # type: ignore
        db_table = "prefecture"
        verbose_name = _("Prefecture")
        verbose_name_plural = _("Prefectures")
        ordering = ("code",)

    def __str__(self):
        return f"{self.name}"
