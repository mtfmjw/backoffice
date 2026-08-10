from django.db import models
from django.utils.translation import gettext_lazy as _


class Holiday(models.Model):
    """
    祝日・休日マスタ（国民の祝日、会社制定休日、法定休日、法定外休日、振替出勤日など）
    """

    class Type(models.TextChoices):
        NATIONAL_HOLIDAY = "national", _("国民の祝日")
        COMPANY_HOLIDAY = "company", _("会社制定休日（夏季・年末年始等）")
        LEGAL_HOLIDAY = "legal", _("法定休日")
        NON_LEGAL_HOLIDAY = "non_legal", _("法定外休日（所定休日）")

    date = models.DateField(_("日付"), unique=True)
    type = models.CharField(_("区分"), max_length=20, choices=Type.choices, default=Type.NATIONAL_HOLIDAY, null=False, blank=False)
    name = models.CharField(_("休日名称"), max_length=100, help_text=_("例: 元日、夏季休暇、創立記念日"), null=False, blank=False)

    class Meta:
        db_table = "holiday"
        verbose_name = _("祝日・休日")
        verbose_name_plural = _("祝日・休日")
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
                return Holiday.Category.NON_LEGAL_HOLIDAY
            elif day.weekday() == 6:  # 日曜日
                return Holiday.Category.LEGAL_HOLIDAY
            elif day.month == 12 and 29 <= day.day <= 31 or day.month == 1 and 1 <= day.day <= 3:  # 年末年始休暇
                return Holiday.Category.COMPANY_HOLIDAY
            else:
                return None

    @staticmethod
    def get_holiday_type_display(day) -> str:
        """祝日・休日の区分を返す"""
        return Holiday.get_holiday_type(day) and Holiday.Category(Holiday.get_holiday_type(day)).label or ""
