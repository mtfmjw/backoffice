from django.db import models
from django.utils.translation import gettext_lazy as _

# 2020年からのカレンダーを表示する
CALENDAR_START_YEAR = 2020


class Holiday(models.Model):
    """
    祝日・休日マスタ（国民の祝日、会社制定休日、法定休日、法定外休日、振替出勤日など）
    """

    class Type(models.TextChoices):
        NATIONAL_HOLIDAY = "national", _("National Holiday")
        COMPANY_HOLIDAY = "company", _("Company Holiday (Summer/New Year, etc.)")
        LEGAL_HOLIDAY = "legal", _("Legal Holiday")
        NON_LEGAL_HOLIDAY = "non_legal", _("Non-Legal Holiday")

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

    @staticmethod
    def get_holiday_type(day) -> str | None:
        """祝日・休日の区分を返す"""
        try:
            holiday = Holiday.objects.get(date=day)
            return holiday.type
        except Holiday.DoesNotExist:
            if day.weekday() == 5:  # 土曜日
                return Holiday.Type.NON_LEGAL_HOLIDAY
            elif day.weekday() == 6:  # 日曜日
                return Holiday.Type.LEGAL_HOLIDAY
            elif day.month == 12 and 29 <= day.day <= 31 or day.month == 1 and 1 <= day.day <= 3:  # 年末年始休暇
                return Holiday.Type.COMPANY_HOLIDAY
            else:
                return None

    @staticmethod
    def get_holiday_type_display(day) -> str:
        """祝日・休日の区分を返す"""
        return Holiday.get_holiday_type(day) and Holiday.Type(Holiday.get_holiday_type(day)).label or ""
