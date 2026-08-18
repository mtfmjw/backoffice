from datetime import date

from django.db import models
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from common.utils import convert2duration


class WorkPattern(models.Model):
    """勤務パターンマスタ（通常・シフト・フレックスなど）"""

    name = models.CharField(_("Work Pattern Name"), max_length=100, unique=True)
    start_time = models.TimeField(_("Standard Start Time"), default="09:30")
    end_time = models.TimeField(_("Standard End Time"), default="18:00")

    lunch_break_start_time = models.TimeField(_("Lunch Break Start Time"), default="12:00")
    lunch_break_end_time = models.TimeField(_("Lunch Break End Time"), default="13:00")
    break1_start_time = models.TimeField(_("Break 1 Start Time"), default="18:00")
    break1_end_time = models.TimeField(_("Break 1 End Time"), default="18:30")
    break2_start_time = models.TimeField(_("Break 2 Start Time"), default="20:00")
    break2_end_time = models.TimeField(_("Break 2 End Time"), default="20:30")
    break3_start_time = models.TimeField(_("Break 3 Start Time"), default="22:30")
    break3_end_time = models.TimeField(_("Break 3 End Time"), default="22:45")
    break4_start_time = models.TimeField(_("Break 4 Start Time"), default="03:00")
    break4_end_time = models.TimeField(_("Break 4 End Time"), default="03:30")
    break5_start_time = models.TimeField(_("Break 5 Start Time"), default="09:00")
    break5_end_time = models.TimeField(_("Break 5 End Time"), default="09:30")

    class Meta:
        db_table = "work_pattern"
        verbose_name = _("Work Pattern")
        verbose_name_plural = _("Work Patterns")
        ordering = ("start_time",)

    def __str__(self):
        return self.name

    def get_standard_duration(self, base_date: date) -> tuple[datetime, datetime]:
        return convert2duration(base_date, self.start_time, self.end_time)

    def get_break_duration(self, base_date: date, break_number: int) -> tuple[datetime, datetime]:
        if break_number == 0:
            return convert2duration(base_date, self.lunch_break_start_time, self.lunch_break_end_time)
        elif break_number == 1:
            return convert2duration(base_date, self.break1_start_time, self.break1_end_time)
        elif break_number == 2:
            return convert2duration(base_date, self.break2_start_time, self.break2_end_time)
        elif break_number == 3:
            return convert2duration(base_date, self.break3_start_time, self.break3_end_time)
        elif break_number == 4:
            return convert2duration(base_date, self.break4_start_time, self.break4_end_time)
        elif break_number == 5:
            return convert2duration(base_date, self.break5_start_time, self.break5_end_time)
        else:
            return None, None
