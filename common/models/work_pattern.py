from datetime import timedelta

from django.db import models
from django.utils.timezone import datetime, localtime
from django.utils.translation import gettext_lazy as _


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

    def get_duration_in_minutes(self, start_time, end_time) -> int:
        """2つの時刻の差を分単位で返す"""

        if not start_time or not end_time:
            return 0

        # Use a dummy anchor date to allow subtraction
        dummy_date = localtime().date()

        dt_start = datetime.combine(dummy_date, start_time)
        dt_end = datetime.combine(dummy_date, end_time)

        # OVERNIGHT SHIFT HANDLING:
        # If end_time is earlier than start_time (e.g., 22:00 to 06:00), push end_time to the next day
        if dt_end <= dt_start:
            dt_end += timedelta(days=1)

        return (dt_end - dt_start).total_seconds() / 60  # Returns the duration in minutes

    def lunch_break_duration(self):
        """ランチ休憩時間を分単位で返す"""
        return self.get_duration_in_minutes(self.lunch_break_start_time, self.lunch_break_end_time)

    def break1_duration(self):
        """休憩1時間を分単位で返す"""
        return self.get_duration_in_minutes(self.break1_start_time, self.break1_end_time)

    def break2_duration(self):
        """休憩2時間を分単位で返す"""
        return self.get_duration_in_minutes(self.break2_start_time, self.break2_end_time)

    def break3_duration(self):
        """休憩3時間を分単位で返す"""
        return self.get_duration_in_minutes(self.break3_start_time, self.break3_end_time)

    def break4_duration(self):
        """休憩4時間を分単位で返す"""
        return self.get_duration_in_minutes(self.break4_start_time, self.break4_end_time)

    def break5_duration(self):
        """休憩5時間を分単位で返す"""
        return self.get_duration_in_minutes(self.break5_start_time, self.break5_end_time)
