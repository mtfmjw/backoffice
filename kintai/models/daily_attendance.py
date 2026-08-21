from datetime import time, timedelta

from django.db import models
from django.utils.timezone import datetime, localtime
from django.utils.translation import gettext_lazy as _

from common.models import WorkPattern
from common.utils import (
    convert2datetime,
    convert2duration,
    duration2minutes,
    get_overlap_duration,
    get_overlap_minutes,
    minutes2str,
)

from .monthly_attendence import MonthlyAttendance

NIGHT_START_TIME = time(22, 0)
NIGHT_END_TIME = time(5, 0)
HALF_DAY_MINUTES = 180  # 半日休暇の時間（分）
TIME_UNIT = 15  # 勤怠計算の時間単位（分）、当該単位で切り捨てて計算する。15分単位で計算する場合は15、30分単位で計算する場合は30を設定する。

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
        ABSENCE = 1, _("Absence")  # 欠勤
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
    note = models.CharField(_("Note"), max_length=255, null=True, blank=True)  # 備考

    clock_in_time = models.DateTimeField(_("Clock In"), null=True, blank=True)  # 出勤
    clock_out_time = models.DateTimeField(_("Clock Out"), null=True, blank=True)  # 退勤
    has_lunch_break = models.BooleanField(_("Lunch Break"), default=True)  # 昼休憩の有無
    has_break1 = models.BooleanField(_("Break 1"), default=True)  # 休憩1の有無
    has_break2 = models.BooleanField(_("Break 2"), default=True)  # 休憩2の有無
    has_break3 = models.BooleanField(_("Break 3"), default=True)  # 休憩3の有無
    has_break4 = models.BooleanField(_("Break 4"), default=True)  # 休憩4の有無
    has_break5 = models.BooleanField(_("Break 5"), default=True)  # 休憩5の有無
    day_absence = models.TimeField(_("Day Absence"), null=True, blank=True)  # 昼間不在時間
    night_absence = models.TimeField(_("Night Absence"), null=True, blank=True)  # 夜間不在時間

    # 日次算出結果を保存するフィールド
    actual_work_minutes = models.PositiveIntegerField(_("Actual Working Time"), null=True, blank=True)  # 実稼働時間（分）
    overtime_minutes = models.PositiveIntegerField(_("Overtime"), null=True, blank=True)  # 残業時間（分）
    night_work_minutes = models.PositiveIntegerField(_("Night Working Time"), null=True, blank=True)  # 深夜残業時間（分）
    late_minutes = models.PositiveIntegerField(_("Late"), null=True, blank=True)  # 遅刻時間（分）
    early_leave_minutes = models.PositiveIntegerField(_("Early Leave"), null=True, blank=True)  # 早退時間（分）

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
            absence_days = f"{_('Absence Days')}：1" if self.date_status == self.DateStatus.ABSENCE else ""
            return f"{default_message}　{working_time}　{overtime}　{night_work_time}　{is_late}　{is_early_leave} {absence_days}"
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
            and self.work_pattern is not None
            and self.clock_in_time is not None
            and self.clock_out_time is not None
        )

    def get_adjusted_work_duration(self) -> tuple[datetime, datetime]:
        """勤怠計算用勤務時間を返す（半休などを考慮して計算）"""
        if not self.is_present():
            return None, None

        clock_in_time = localtime(self.clock_in_time)
        clock_out_time = localtime(self.clock_out_time)
        # 出勤時間は15分単位で切り上げる、例えば、8:57は9:00に切り上げ、9:00は9:00のまま、9:01は9:15に切り上げる
        start_time = time(hour=clock_in_time.hour, minute=((clock_in_time.minute + TIME_UNIT - 1) // TIME_UNIT) * TIME_UNIT)
        # 退勤時間は15分単位で切り捨てる、例えば、17:57は17:45に切り捨て、18:00は18:00のまま、18:01は18:00に切り捨てる
        end_time = time(hour=clock_out_time.hour, minute=(clock_out_time.minute // TIME_UNIT) * TIME_UNIT)
        return convert2duration(self.day, start_time, end_time)

    def get_standard_work_duration(self) -> tuple[datetime, datetime]:
        """標準勤務期間を返す"""
        if self.work_pattern is None or self.work_pattern.start_time is None or self.work_pattern.end_time is None:
            return None, None

        start_time, end_time = convert2duration(self.day, self.work_pattern.start_time, self.work_pattern.end_time)
        if self.date_status == self.DateStatus.MORNING_PAID_LEAVE:
            # 午前半休後の勤務開始時刻を設定
            if self.work_pattern.half_day_time is not None:
                start_time = convert2datetime(self.day, self.work_pattern.half_day_time)
            else:
                start_time += timedelta(minutes=HALF_DAY_MINUTES)
        elif self.date_status == self.DateStatus.AFTERNOON_PAID_LEAVE:
            # 午後半休前の勤務終了時刻を設定
            if self.work_pattern.half_day_time is not None:
                end_time = convert2datetime(self.day, self.work_pattern.half_day_time)
            else:
                end_time = start_time + timedelta(minutes=HALF_DAY_MINUTES)
        return start_time, end_time

    def get_late_minutes(self) -> int:
        """遅刻時間を分単位で返す"""
        if not self.is_present():
            return 0

        standard_start_time, __ = self.get_standard_work_duration()
        if standard_start_time is None:
            return 0

        actual_start_time, __ = self.get_adjusted_work_duration()
        if actual_start_time > standard_start_time:
            return int((actual_start_time - standard_start_time).total_seconds() // 60)
        return 0

    def get_early_leave_minutes(self) -> int:
        """早退時間を分単位で返す"""
        if not self.is_present():
            return 0

        __, standard_end_time = self.get_standard_work_duration()
        if standard_end_time is None:
            return 0

        __, actual_end_time = self.get_adjusted_work_duration()
        if actual_end_time < standard_end_time:
            return int((standard_end_time - actual_end_time).total_seconds() // 60)
        return 0

    def has_breaks(self) -> list[bool]:
        """休憩があるかどうかを返す"""
        return [self.has_lunch_break, self.has_break1, self.has_break2, self.has_break3, self.has_break4, self.has_break5]

    def get_net_work_minutes(self, work_duration: tuple[datetime, datetime]) -> int:
        """指定された勤務時間より休憩時間を除いた実質勤務時間を返す"""

        if not self.is_present():
            return 0

        work_start, __ = work_duration
        if work_start is None:
            return 0

        actual_break_minutes = 0
        for break_duration, has_break in zip(self.work_pattern.get_break_durations(), self.has_breaks()):
            if not has_break:
                continue
            break_start, break_end = break_duration
            if work_start.time() > break_start:
                break_duration = convert2duration(work_start.date() + timedelta(days=1), break_start, break_end)
            else:
                break_duration = convert2duration(work_start.date(), break_start, break_end)
            actual_break_minutes += get_overlap_minutes(work_duration, break_duration)
        return max(duration2minutes(work_duration) - actual_break_minutes, 0)

    # 管理画面や画面表示用に「○時間×分」で取得するヘルパーメソッド
    def get_actual_work_minutes(self) -> int:
        """実労働時間を分単位で返す"""
        if self.is_present():
            net_work_minutes = self.get_net_work_minutes(self.get_adjusted_work_duration())
            day_absence_minutes = (self.day_absence.hour * 60 + self.day_absence.minute) if self.day_absence else 0
            night_absence_minutes = (self.night_absence.hour * 60 + self.night_absence.minute) if self.night_absence else 0
            return max(net_work_minutes - day_absence_minutes - night_absence_minutes, 0)
        return 0

    def get_overtime_minutes(self) -> int:
        """残業時間を分単位で返す"""
        if self.is_present() is False or self.work_pattern is None:
            return 0

        standard_work_minutes = 0
        if self.work_pattern.start_time is not None and self.work_pattern.end_time is not None:
            standard_work_minutes = self.get_net_work_minutes(self.get_standard_work_duration())
        else:
            standard_work_minutes = self.work_pattern.get_standard_work_minutes()

        return max(self.get_actual_work_minutes() - standard_work_minutes, 0)

    def get_night_work_minutes(self) -> int:
        """深夜労働時間を分単位で返す、深夜労働時間は日をまたがることを前提とする。"""
        if self.is_present() is False:
            return 0

        work_duration = self.get_adjusted_work_duration()
        work_start, __ = work_duration
        if work_start.time() >= NIGHT_END_TIME:
            night_duration = convert2duration(self.day, NIGHT_START_TIME, NIGHT_END_TIME)
            night_work_duration = get_overlap_duration(night_duration, work_duration)
            total_night_work_minutes = self.get_net_work_minutes(night_work_duration)
        else:
            night_duration1 = convert2duration(self.day, time(0, 0), NIGHT_END_TIME)
            night_duration2 = convert2duration(self.day, NIGHT_START_TIME, time(0, 0))
            night_work_duration1 = get_overlap_duration(night_duration1, work_duration)
            night_work_duration2 = get_overlap_duration(night_duration2, work_duration)
            total_night_work_minutes = self.get_net_work_minutes(night_work_duration1) + self.get_net_work_minutes(night_work_duration2)

        return max(total_night_work_minutes - (self.night_absence.hour * 60 + self.night_absence.minute if self.night_absence else 0), 0)

    def get_paid_leave_days(self) -> float:
        """有給休暇取得日数を返す"""
        if self.date_status == self.DateStatus.PAID_LEAVE:
            return 1
        elif self.date_status in [self.DateStatus.MORNING_PAID_LEAVE, self.DateStatus.AFTERNOON_PAID_LEAVE]:
            return 0.5
        return 0

    def save(self, *args, **kwargs):
        """日次勤怠を保存する際に、月次勤怠の実労働時間、残業時間、深夜労働時間を更新する"""

        self.actual_work_minutes = self.get_actual_work_minutes() if self.is_present() else 0
        self.overtime_minutes = self.get_overtime_minutes() if self.is_present() else 0
        self.night_work_minutes = self.get_night_work_minutes() if self.is_present() else 0
        self.late_minutes = self.get_late_minutes() if self.is_present() else 0
        self.early_leave_minutes = self.get_early_leave_minutes() if self.is_present() else 0
        super().save(*args, **kwargs)
