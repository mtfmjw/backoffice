from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import MemberScopedBaseModel

# 2020年からのカレンダーを表示する
CALENDAR_START_YEAR = 2020


class Holiday(MemberScopedBaseModel):
    """
    祝日・休日マスタ（国民の祝日、会社制定休日、法定休日、法定外休日、振替出勤日など）
    """

    class Type(models.TextChoices):
        NATIONAL_HOLIDAY = "national", _("National Holiday")
        COMPANY_HOLIDAY = "company", _("Company Holiday (Summer/New Year, etc.)")

    date = models.DateField(_("Date"), unique=True)
    type = models.CharField(_("Holiday Type"), max_length=20, choices=Type.choices, default=Type.NATIONAL_HOLIDAY, null=False, blank=False)
    name = models.CharField(
        _("Holiday Name"), max_length=100, help_text=_("e.g., New Year's Day, Summer Vacation, Foundation Day"), null=False, blank=False
    )

    class Meta:
        db_table = "holiday"
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ("date",)

    def __str__(self):
        return f"{self.date} : {self.name} "
