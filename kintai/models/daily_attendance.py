from datetime import timedelta

from django.db import models
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from common.models import WorkPattern
from common.utils import convert2duration, duration2minutes, get_overlap_minutes, minutes2str, minutes2str_ja
from kintai.models.monthly_attendence import HALF_DAY_MINUTES, NIGHT_END_TIME, NIGHT_START_TIME, MonthlyAttendance

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

    class Meta:
        db_table = "attendance_daily"
        verbose_name = _("Daily Attendance")
        verbose_name_plural = _("Daily Attendances")
        unique_together = ("monthly_attendance", "day")  # 1人1日1レコードに制限
        ordering = ("day",)

    def __str__(self):
        default_message = f"{self.day.strftime('%Y年%m月%d日')} - {self.get_date_type_display()}"
        if self.is_present():
            working_time = f"{_('Actual Working Time')}：{minutes2str(self.get_actual_work_minutes())}"
            overtime = f"{_('Overtime')}：{minutes2str(self.get_overtime_minutes())}"
            night_work_time = f"{_('Night Working Time')}：{minutes2str(self.get_night_work_minutes())}"
            return f"{default_message}　{working_time}　{overtime}　{night_work_time}"
        else:
            return default_message

    def is_work_day(self):
        """勤務日かどうかを返す"""
        return self.date_type == self.DateType.WORK_DAY

    def is_present(self):
        """就業状態かどうかを返す"""
        return (
            self.date_status == self.DateStatus.PRESENT
            or self.date_status == self.DateStatus.MORNING_PAID_LEAVE
            or self.date_status == self.DateStatus.AFTERNOON_PAID_LEAVE
        )

    def standard_working_duration(self) -> tuple[datetime, datetime]:
        """標準勤務開始時刻を返す（半休などを考慮して計算）"""
        if self.work_pattern is None:
            return None, None

        start_time, end_time = self.work_pattern.get_standard_duration(self.day)
        if self.date_status == self.DateStatus.MORNING_PAID_LEAVE:
            # 午前半休の勤務開始時刻を設定
            start_time += timedelta(minutes=HALF_DAY_MINUTES)
        elif self.date_status == self.DateStatus.AFTERNOON_PAID_LEAVE:
            end_time = start_time + timedelta(minutes=HALF_DAY_MINUTES)
        return start_time, end_time

    def get_late_minutes(self) -> int:
        """遅刻時間を分単位で返す"""
        if not self.is_present() or self.clock_in_time is None or self.clock_out_time is None:
            return 0

        start_time, end_time = self.standard_working_duration()
        if start_time is not None and end_time is not None and self.clock_in_time > start_time:
            return int((self.clock_in_time - start_time).total_seconds() // 60)
        return 0

    def get_early_leave_minutes(self) -> int:
        """早退時間を分単位で返す"""
        if not self.is_present() or self.clock_in_time is None or self.clock_out_time is None:
            return 0

        start_time, end_time = self.standard_working_duration()
        if start_time is not None and end_time is not None and self.clock_out_time < end_time:
            return int((end_time - self.clock_out_time).total_seconds() // 60)
        return 0

    def has_break(self, break_number) -> bool:
        if break_number == 0:
            return self.has_lunch_break
        elif break_number == 1:
            return self.has_break1
        elif break_number == 2:
            return self.has_break2
        elif break_number == 3:
            return self.has_break3
        elif break_number == 4:
            return self.has_break4
        elif break_number == 5:
            return self.has_break5
        else:
            return False

    def get_break_minutes(self, break_number: int) -> int:
        """休憩時間を分単位で返す"""
        if not self.is_present() or self.work_pattern is None or not self.has_break(break_number):
            return 0

        return get_overlap_minutes((self.clock_in_time, self.clock_out_time), self.work_pattern.get_break_duration(self.day, break_number))

    # 管理画面や画面表示用に「○時間×分」で取得するヘルパーメソッド
    def get_actual_work_minutes(self) -> int:
        """実労働時間を分単位で返す"""
        if self.is_present() and self.clock_in_time and self.clock_out_time:
            total_work_minutes = duration2minutes(self.clock_in_time, self.clock_out_time)
            total_break_minutes = sum(self.get_break_minutes(i) for i in range(6))
            return max(total_work_minutes - total_break_minutes - (self.other_break_minutes or 0), 0)
        return 0

    def display_work_time(self):
        """実労働時間を「○時間×分」の形式で返す"""
        return minutes2str_ja(self.get_actual_work_minutes())

    def get_overtime_minutes(self) -> int:
        """残業時間を分単位で返す"""
        actual_work_minutes = self.get_actual_work_minutes()
        start, end = self.standard_working_duration()
        standard_working_minutes = duration2minutes(start, end)
        return max(actual_work_minutes - standard_working_minutes, 0)

    def display_overtime(self):
        """残業時間を「○時間×分」の形式で返す"""
        return minutes2str_ja(self.get_overtime_minutes())

    def get_night_work_duration(self):
        return convert2duration(self.day, NIGHT_START_TIME, NIGHT_END_TIME)

    def get_night_break_minutes(self, break_number: int) -> int:
        """休憩時間を分単位で返す"""
        if not self.is_present() or self.work_pattern is None or not self.has_break(break_number):
            return 0

        return get_overlap_minutes(self.get_night_work_duration(), self.work_pattern.get_break_duration(self.day, break_number))

    def get_night_work_minutes(self) -> int:
        """深夜労働時間を分単位で返す"""
        total_night_minutes = get_overlap_minutes(self.get_night_work_duration(), (self.clock_in_time, self.clock_out_time))
        night_break_minutes = sum(self.get_night_break_minutes(i) for i in range(6))
        return max(total_night_minutes - night_break_minutes, 0)

    def display_night_work_time(self) -> str:
        """深夜労働時間を「○時間×分」の形式で返す"""
        return minutes2str_ja(self.get_night_work_minutes())

    def get_paid_leave_days(self) -> float:
        """有給休暇取得日数を返す"""
        if self.date_status == self.DateStatus.PAID_LEAVE:
            return 1
        elif self.date_status in [self.DateStatus.MORNING_PAID_LEAVE, self.DateStatus.AFTERNOON_PAID_LEAVE]:
            return 0.5
        return 0
