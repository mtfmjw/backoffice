from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import get_duration_in_minutes


class WorkPattern(models.Model):
    """勤務形態マスタ（通常・シフト・フレックスなど）"""

    name = models.CharField(_("勤務形態名"), max_length=100)
    start_time = models.TimeField(_("標準始業時刻"), default="09:30")
    end_time = models.TimeField(_("標準終業時刻"), default="18:00")

    lunch_break_start_time = models.TimeField(_("昼休開始時刻"), default="12:00")
    lunch_break_end_time = models.TimeField(_("昼休終了時刻"), default="13:00")
    break1_start_time = models.TimeField(_("休憩1開始時刻"), default="18:00")
    break1_end_time = models.TimeField(_("休憩1終了時刻"), default="18:30")
    break2_start_time = models.TimeField(_("休憩2開始時刻"), default="20:00")
    break2_end_time = models.TimeField(_("休憩2終了時刻"), default="20:30")
    break3_start_time = models.TimeField(_("休憩3開始時刻"), default="22:30")
    break3_end_time = models.TimeField(_("休憩3終了時刻"), default="22:45")
    break4_start_time = models.TimeField(_("休憩4開始時刻"), default="03:00")
    break4_end_time = models.TimeField(_("休憩4終了時刻"), default="03:30")
    break5_start_time = models.TimeField(_("休憩5開始時刻"), default="09:00")
    break5_end_time = models.TimeField(_("休憩5終了時刻"), default="09:30")

    class Meta:
        db_table = "work_pattern"
        verbose_name = _("勤務形態")
        verbose_name_plural = _("勤務形態")
        ordering = ("start_time",)

    def __str__(self):
        return self.name

    def lunch_break_duration(self):
        """ランチ休憩時間を分単位で返す"""
        return get_duration_in_minutes(self.lunch_break_start_time, self.lunch_break_end_time)

    def break1_duration(self):
        """休憩1時間を分単位で返す"""
        return get_duration_in_minutes(self.break1_start_time, self.break1_end_time)

    def break2_duration(self):
        """休憩2時間を分単位で返す"""
        return get_duration_in_minutes(self.break2_start_time, self.break2_end_time)

    def break3_duration(self):
        """休憩3時間を分単位で返す"""
        return get_duration_in_minutes(self.break3_start_time, self.break3_end_time)

    def break4_duration(self):
        """休憩4時間を分単位で返す"""
        return get_duration_in_minutes(self.break4_start_time, self.break4_end_time)

    def break5_duration(self):
        """休憩5時間を分単位で返す"""
        return get_duration_in_minutes(self.break5_start_time, self.break5_end_time)
