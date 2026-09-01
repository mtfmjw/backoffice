from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import WorkPattern
from common.utils import (
    minutes2str,
)
from kintai.const import WEEKDAYS, DateStatus, DateType

from .monthly_attendance import MonthlyAttendance


class DailyAttendance(models.Model):
    """日次勤怠テーブル（1人1日あたりの確定データ）"""

    monthly_attendance = models.ForeignKey(
        MonthlyAttendance, on_delete=models.CASCADE, related_name="daily_attendances", verbose_name=_("Monthly Attendance")
    )  # 月次勤怠
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, verbose_name=_("Work Pattern"), null=True, blank=True)  # 就業パターン
    day = models.DateField(_("Day"))  # 日付
    date_type = models.IntegerField(_("Date Type"), choices=DateType.choices, default=DateType.WORK_DAY)  # 勤務日分類
    date_status = models.IntegerField(_("Date Status"), choices=DateStatus.choices, default=DateStatus.PRESENT, null=True, blank=True)  # 就業区分
    note = models.CharField(_("Note"), max_length=255, null=True, blank=True)  # 備考

    clock_in_time = models.DateTimeField(_("Clock In"), null=True, blank=True)  # 出勤
    clock_out_time = models.DateTimeField(_("Clock Out"), null=True, blank=True)  # 退勤
    has_lunch_break = models.BooleanField(_("Lunch Break"), default=True)  # 昼休憩の有無
    has_break1 = models.BooleanField(_("Break 1"), default=True)  # 休憩1の有無
    has_break2 = models.BooleanField(_("Break 2"), default=True)  # 休憩2の有無
    has_break3 = models.BooleanField(_("Break 3"), default=True)  # 休憩3の有無
    has_break4 = models.BooleanField(_("Break 4"), default=True)  # 休憩4の有無
    has_break5 = models.BooleanField(_("Break 5"), default=True)  # 休憩5の有無
    absence_start = models.TimeField(_("Absence Start"), null=True, blank=True)  # 不在時間開始時刻
    absence_end = models.TimeField(_("Absence End"), null=True, blank=True)  # 不在時間終了時刻

    # 日次算出結果を保存するフィールド
    actual_work_minutes = models.PositiveIntegerField(_("Actual Working Time"), default=0, null=True, blank=True)  # 実稼働時間（分）
    late_minutes = models.PositiveIntegerField(_("Late"), default=0, null=True, blank=True)  # 遅刻時間（分）
    early_leave_minutes = models.PositiveIntegerField(_("Early Leave"), default=0, null=True, blank=True)  # 早退時間（分）
    overtime_125 = models.PositiveIntegerField(_("Overtime 1.25"), default=0, null=True, blank=True)  # 普通残業時間（1.25）
    overtime_150 = models.PositiveIntegerField(_("Overtime 1.50"), default=0, null=True, blank=True)  # 普通深夜残業時間（1.50）
    night_time_025 = models.PositiveIntegerField(_("Night Overtime 0.25"), default=0, null=True, blank=True)  # 深夜就業時間（0.25）
    off_day_125 = models.PositiveIntegerField(_("Off Day 1.25"), default=0, null=True, blank=True)  # 休日出勤時間（1.25）
    off_day_150 = models.PositiveIntegerField(_("Off Day 1.50"), default=0, null=True, blank=True)  # 休日深夜出勤時間（1.50）
    holiday_135 = models.PositiveIntegerField(_("Holiday 1.35"), default=0, null=True, blank=True)  # 法定休日出勤時間（1.35）
    holiday_160 = models.PositiveIntegerField(_("Holiday 1.60"), default=0, null=True, blank=True)  # 法定休日深夜出勤時間（1.60）

    class Meta:
        db_table = "attendance_daily"
        verbose_name = _("Daily Attendance")
        verbose_name_plural = _("Daily Attendances")
        unique_together = ("monthly_attendance", "day")  # 1人1日1レコードに制限
        ordering = ("monthly_attendance", "day")

    def __str__(self):
        default_message = f"{self.day.strftime('%Y年%m月%d日')}({WEEKDAYS[self.day.isoweekday() - 1]}) - {self.get_date_type_display()}"
        if self.is_present():
            working_time = f"{_('Actual Working Time')}：{minutes2str(self.actual_work_minutes)}" if self.actual_work_minutes is not None else ""
            is_late = f"{_('Late')}：{minutes2str(self.late_minutes)}" if self.late_minutes else ""
            is_early_leave = f"{_('Early Leave')}：{minutes2str(self.early_leave_minutes)}" if self.early_leave_minutes else ""
            absence_days = f"{_('Absence Days')}：1" if self.date_status == DateStatus.ABSENCE else ""
            return f"{default_message}　{working_time}　{is_late}　{is_early_leave} {absence_days}"
        else:
            return default_message

    def is_work_day(self):
        """勤務日かどうかを返す"""
        return self.date_type == DateType.WORK_DAY

    def is_present(self):
        """就業状態かどうかを返す"""
        return (
            (
                self.date_status == DateStatus.PRESENT
                or self.date_status == DateStatus.MORNING_PAID_LEAVE
                or self.date_status == DateStatus.AFTERNOON_PAID_LEAVE
            )
            and self.work_pattern is not None
            and self.clock_in_time is not None
            and self.clock_out_time is not None
        )
