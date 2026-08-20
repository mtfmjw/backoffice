from datetime import time, timedelta

from django.db import models
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from common.models import WorkPattern
from common.utils import (
    convert2duration,
    convert2localtime,
    duration2minutes,
    get_overlap_duration,
    get_overlap_minutes,
    minutes2str,
)

from .monthly_attendence import MonthlyAttendance

NIGHT_START_TIME = time(22, 0)
NIGHT_END_TIME = time(5, 0)
HALF_DAY_MINUTES = 180  # 半日休暇の時間（分）

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


class DailyAttendance(models.Model):
    """日次勤怠テーブル（1人1日あたりの確定データ）"""

    class DateType(models.IntegerChoices):
        """勤務日分類"""

        WORK_DAY = 0, _("Work Day")  # 平日
        SCHEDULED_DAY_OFF = 1, _("Scheduled Day Off")  # 所定休日
        STATUTORY_DAY_OFF = 2, _("Statutory Day Off")  # 法定休日
        NATIONAL_HOLIDAY = 3, _("National Holiday")  # 国民の祝日
        TRANSFER_HOLIDAY = 4, _("Transfer Holiday")  # 振替休日、祝日が土日と重なった場合に、翌日を振替休日（法定休日）とする

    class DateStatus(models.IntegerChoices):
        """就業区分"""

        PRESENT = 0, _("Present")  # 出勤
        ABSENCE = 1, _("Absent")  # 欠勤
        MORNING_PAID_LEAVE = 2, _("Morning Half-Day Leave")  # 午前半休
        AFTERNOON_PAID_LEAVE = 3, _("Afternoon Half-Day Leave")  # 午後半休
        PAID_LEAVE = 4, _("Paid Leave")  # 有給休暇
        # 特別休暇：結婚、忌引、出産、育児、介護などの理由で取得する休暇。会社の規定に基づき、特別な理由で取得する休暇であり、通常の有給休暇とは異なる。
        SPECIAL_PAID_LEAVE = 5, _("Special Paid Leave")  # 特別休暇
        # 振替休日：出勤する前に、あらかじめ休日と入れ替えた日。休日と労働日を交換したため、出勤日（元の休日）は通常の労働日となる。
        SUBSTITUTE_HOLIDAY = 6, _("Substitute Holiday")  # 振替休日
        # 代休日：休日に出勤して、後日休んだ日。休日に出勤したため、出勤日（元の休日）は休日出勤となる。
        COMPENSATORY_HOLIDAY = 7, _("Compensatory Holiday")  # 代休
        SP5 = 8, _("SP5")  # 4-5月：ゴールデンウイーク2日、7-9月：夏季休暇3日、12/29-1/3：年末年始休暇6日

    monthly_attendance = models.ForeignKey(
        MonthlyAttendance, on_delete=models.CASCADE, related_name="daily_attendances", verbose_name=_("Monthly Attendance")
    )  # 月次勤怠
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, verbose_name=_("Work Pattern"), null=True, blank=True)  # 就業パターン
    day = models.DateField(_("Day"))  # 日付
    date_type = models.IntegerField(_("Date Type"), choices=DateType.choices, default=DateType.WORK_DAY)  # 勤務日分類
    date_status = models.IntegerField(_("Date Status"), choices=DateStatus.choices, default=DateStatus.PRESENT, null=True, blank=True)  # 就業区分
    substitute_day = models.DateField(_("Substitute Day"), null=True, blank=True)  # 振替休日、代休日の元の休日
    note = models.CharField(_("Note"), max_length=255, null=True, blank=True)  # 備考

    clock_in_time = models.DateTimeField(_("Clock In"), null=True, blank=True)  # 出勤
    clock_out_time = models.DateTimeField(_("Clock Out"), null=True, blank=True)  # 退勤
    has_lunch_break = models.BooleanField(_("Lunch Break"), default=True)  # 昼休憩の有無
    has_break1 = models.BooleanField(_("Break 1"), default=True)  # 休憩1の有無
    has_break2 = models.BooleanField(_("Break 2"), default=True)  # 休憩2の有無
    has_break3 = models.BooleanField(_("Break 3"), default=True)  # 休憩3の有無
    has_break4 = models.BooleanField(_("Break 4"), default=True)  # 休憩4の有無
    has_break5 = models.BooleanField(_("Break 5"), default=True)  # 休憩5の有無
    other_break_minutes = models.PositiveIntegerField(_("Other Break (min)"), default=0, null=True, blank=True)  # 不在時間（分）

    # 日次算出結果を保存するフィールド
    actual_work_minutes = models.PositiveIntegerField(_("Actual Working Time"), null=True, blank=True)
    overtime_minutes = models.PositiveIntegerField(_("Overtime"), null=True, blank=True)
    night_work_minutes = models.PositiveIntegerField(_("Night Working Time"), null=True, blank=True)
    late_minutes = models.PositiveIntegerField(_("Late"), null=True, blank=True)
    early_leave_minutes = models.PositiveIntegerField(_("Early Leave"), null=True, blank=True)

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
            overtime = f"{_('Overtime')}：{minutes2str(self.overtime_minutes)}" if self.overtime_minutes is not None else ""
            night_work_time = f"{_('Night Working Time')}：{minutes2str(self.night_work_minutes)}" if self.night_work_minutes is not None else ""
            is_late = f"{_('Late')}：{minutes2str(self.late_minutes)}" if self.late_minutes else ""
            is_early_leave = f"{_('Early Leave')}：{minutes2str(self.early_leave_minutes)}" if self.early_leave_minutes else ""
            return f"{default_message}　{working_time}　{overtime}　{night_work_time}　{is_late}　{is_early_leave}"
        else:
            return default_message

    def is_work_day(self):
        """勤務日かどうかを返す"""
        return self.date_type == self.DateType.WORK_DAY

    def is_present(self):
        """就業状態かどうかを返す"""
        return (
            (
                self.date_status == self.DateStatus.PRESENT
                or self.date_status == self.DateStatus.MORNING_PAID_LEAVE
                or self.date_status == self.DateStatus.AFTERNOON_PAID_LEAVE
            )
            and self.clock_in_time is not None
            and self.clock_out_time is not None
        )

    def get_actual_work_duration(self) -> tuple[datetime, datetime]:
        """勤務時間を返す"""
        if not self.is_present():
            return None, None
        return convert2localtime(self.clock_in_time), convert2localtime(self.clock_out_time)

    def get_standard_work_duration(self) -> tuple[datetime, datetime]:
        """標準勤務開始時刻を返す（半休などを考慮して計算）"""
        if self.work_pattern is None:
            return None, None

        start_time, end_time = convert2duration(self.day, self.work_pattern.start_time, self.work_pattern.end_time)
        if self.date_status == self.DateStatus.MORNING_PAID_LEAVE:
            # 午前半休の勤務開始時刻を設定
            start_time += timedelta(minutes=HALF_DAY_MINUTES)
        elif self.date_status == self.DateStatus.AFTERNOON_PAID_LEAVE:
            end_time = start_time + timedelta(minutes=HALF_DAY_MINUTES)
        return start_time, end_time

    def get_late_minutes(self) -> int:
        """遅刻時間を分単位で返す"""
        if not self.is_present():
            return 0

        actual_start_time, __ = self.get_actual_work_duration()
        standard_start_time, __ = self.get_standard_work_duration()
        if actual_start_time > standard_start_time:
            return int((actual_start_time - standard_start_time).total_seconds() // 60)
        return 0

    def get_early_leave_minutes(self) -> int:
        """早退時間を分単位で返す"""
        if not self.is_present():
            return 0

        __, actual_end_time = self.get_actual_work_duration()
        __, standard_end_time = self.get_standard_work_duration()
        if actual_end_time < standard_end_time:
            return int((standard_end_time - actual_end_time).total_seconds() // 60)
        return 0

    def get_actual_break_duration(self, break_duration: tuple[time, time], work_duration: tuple[datetime, datetime]) -> tuple[datetime, datetime]:
        """指定された休憩期間と勤務時間の重なった時間帯を返す"""
        break_start, break_end = break_duration
        work_start, __ = work_duration
        if work_start.time() > break_start:
            break_duration_datetime = convert2duration(work_start.date() + timedelta(days=1), break_start, break_end)
        else:
            break_duration_datetime = convert2duration(work_start.date(), break_start, break_end)
        return break_duration_datetime

    def get_break_minutes(self, break_number: int, work_duration: tuple[datetime, datetime]) -> int:
        """指定された期間と標準休憩期間の重なった分数を返す、標準休憩期間は日をまたがらないことを前提とする"""

        if not self.is_present() or self.work_pattern is None:
            return 0

        start_time, end_time = work_duration
        if start_time is None or end_time is None:
            return 0

        if break_number == 0 and self.has_lunch_break:
            break_duration = self.get_actual_break_duration(
                (self.work_pattern.lunch_break_start_time, self.work_pattern.lunch_break_end_time), work_duration
            )
        elif break_number == 1 and self.has_break1:
            break_duration = self.get_actual_break_duration((self.work_pattern.break1_start_time, self.work_pattern.break1_end_time), work_duration)
        elif break_number == 2 and self.has_break2:
            break_duration = self.get_actual_break_duration((self.work_pattern.break2_start_time, self.work_pattern.break2_end_time), work_duration)
        elif break_number == 3 and self.has_break3:
            break_duration = self.get_actual_break_duration((self.work_pattern.break3_start_time, self.work_pattern.break3_end_time), work_duration)
        elif break_number == 4 and self.has_break4:
            break_duration = self.get_actual_break_duration((self.work_pattern.break4_start_time, self.work_pattern.break4_end_time), work_duration)
        elif break_number == 5 and self.has_break5:
            break_duration = self.get_actual_break_duration((self.work_pattern.break5_start_time, self.work_pattern.break5_end_time), work_duration)

        return get_overlap_minutes(work_duration, break_duration)

    # 管理画面や画面表示用に「○時間×分」で取得するヘルパーメソッド
    def get_actual_work_minutes(self) -> int:
        """実労働時間を分単位で返す"""
        if self.is_present():
            actual_work_duration = self.get_actual_work_duration()
            total_work_minutes = duration2minutes(actual_work_duration)
            total_break_minutes = sum(self.get_break_minutes(i, actual_work_duration) for i in range(6))
            return max(total_work_minutes - total_break_minutes - (self.other_break_minutes or 0), 0)
        return 0

    def get_standard_work_minutes(self) -> int:
        """標準休憩時間を分単位で返す"""
        if not self.is_present() or self.work_pattern is None:
            return 0
        return self.work_pattern.get_standard_work_minutes()

    def get_overtime_minutes(self) -> int:
        """残業時間を分単位で返す"""
        return max(self.get_actual_work_minutes() - self.get_standard_work_minutes(), 0)

    def get_night_work_minutes(self) -> int:
        """深夜労働時間を分単位で返す、深夜労働時間は日をまたがることを前提とする。"""
        if self.is_present() is False:
            return 0

        work_duration = self.get_actual_work_duration()
        work_start, __ = work_duration
        if work_start.time() >= NIGHT_END_TIME:
            night_duration = convert2duration(self.day, NIGHT_START_TIME, NIGHT_END_TIME)
            night_work_duration = get_overlap_duration(night_duration, work_duration)
            total_night_work_minutes = duration2minutes(night_work_duration)
            night_break_minutes = sum(self.get_break_minutes(i, night_work_duration) for i in range(6))
            total_night_work_minutes -= night_break_minutes
        else:
            night_duration1 = convert2duration(self.day, time(0, 0), NIGHT_END_TIME)
            night_duration2 = convert2duration(self.day, NIGHT_START_TIME, time(0, 0))
            night_work_duration1 = get_overlap_duration(night_duration1, work_duration)
            night_work_duration2 = get_overlap_duration(night_duration2, work_duration)
            total_night_work_minutes = duration2minutes(night_work_duration1) + duration2minutes(night_work_duration2)
            night_break_minutes = sum(self.get_break_minutes(i, night_work_duration1) for i in range(6)) + sum(
                self.get_break_minutes(i, night_work_duration2) for i in range(6)
            )
            total_night_work_minutes -= night_break_minutes

        return max(total_night_work_minutes, 0)

    def get_paid_leave_days(self) -> float:
        """有給休暇取得日数を返す"""
        if self.date_status == self.DateStatus.PAID_LEAVE:
            return 1
        elif self.date_status in [self.DateStatus.MORNING_PAID_LEAVE, self.DateStatus.AFTERNOON_PAID_LEAVE]:
            return 0.5
        return 0

    def save(self, *args, **kwargs):
        """日次勤怠を保存する際に、月次勤怠の実労働時間、残業時間、深夜労働時間を更新する"""

        self.actual_work_minutes = self.get_actual_work_minutes()
        self.overtime_minutes = self.get_overtime_minutes()
        self.night_work_minutes = self.get_night_work_minutes()
        self.late_minutes = self.get_late_minutes()
        self.early_leave_minutes = self.get_early_leave_minutes()
        super().save(*args, **kwargs)
