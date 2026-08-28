from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import MemberScopedModel
from .municipality import Municipality


class Postcode(MemberScopedModel):
    """郵便番号マスタ"""

    postcode = models.CharField(_("Postcode"), max_length=7, null=False, blank=False)  # 郵便番号
    municipality = models.ForeignKey(Municipality, verbose_name=_("Municipality"), on_delete=models.DO_NOTHING, blank=True, null=True)  # 市区町村
    town_name = models.CharField(_("Town Name"), max_length=1000, null=True, blank=True, default="")  # 町域名
    town_name_kana = models.CharField(_("Town Name Kana"), max_length=1000, null=True, blank=True, default="")  # 町域名カナ

    class Meta:  # type: ignore
        db_table = "postcode"
        verbose_name = _("Postcode")
        verbose_name_plural = _("Postcodes")
        ordering = ("postcode",)
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["postcode", "municipality", "town_name", "town_name_kana"],
                name="unique_postcode_postcode_town_name",
            )
        ]

    def __str__(self):
        return f"{self.postcode}"


class PostcodeImport(models.Model):
    postcode = models.CharField(_("Postcode"), max_length=7, null=False, blank=False)  # 郵便番号
    municipality_code = models.CharField(_("Municipality Code"), max_length=10, null=True, blank=True)  # 市区町村コード
    town_name = models.CharField(_("Town Name"), max_length=1000, null=True, blank=True, default="")  # 町域名
    town_name_kana = models.CharField(_("Town Name Kana"), max_length=1000, null=True, blank=True, default="")  # 町域名カナ

    class Meta:  # type: ignore
        db_table = "tmp_postcode_import"
