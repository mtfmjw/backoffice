from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.prefecture import Prefecture


class Municipality(models.Model):
    """市区町村マスタ"""

    code = models.CharField(_("Municipality Code"), max_length=5, unique=True)  # 市区町村コード
    name = models.CharField(_("Municipality Name"), max_length=100, blank=True, null=True)  # 市区町村名
    name_kana = models.CharField(_("Municipality Name Kana"), max_length=100, blank=True, null=True)  # 市区町村名
    prefecture = models.ForeignKey(Prefecture, verbose_name=_("Prefecture"), on_delete=models.DO_NOTHING, blank=True, null=True)  # 都道府県コード

    class Meta:  # type: ignore
        db_table = "municipality"
        verbose_name = _("Municipality")
        verbose_name_plural = _("Municipalities")
        ordering = ("code",)

    def __str__(self):
        return f"{self.name}({self.code})"
