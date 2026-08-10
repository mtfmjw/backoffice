from datetime import timedelta

from django.db import models
from django.db.models import Case, IntegerField, Value, When
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from common.models import WorkPattern, get_duration_in_minutes
from kintai.models.monthly_attendence import HALF_DAY_MINUTES, MonthlyAttendance


class DailyAttendance(models.Model):
    """日次勤怠テーブル（1人1日あたりの確定データ）"""

    class DateType(models.IntegerChoices):
        PRESENT = 0, _("出勤")
        ABSENT = 1, _("欠勤")
        MORNING_PAID_LEAVE = 2, _("午前半休")
        AFTERNOON_PAID_LEAVE = 3, _("午後半休")
        PAID_LEAVE = 4, _("有休")
        SPECIAL_LEAVE = 5, _("特別休暇")
        HOLIDAY = 6, _("休日")

    monthly_attendance = models.ForeignKey(MonthlyAttendance, on_delete=models.CASCADE, related_name="daily_attendances", verbose_name=_("月次勤怠"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("勤務形態"))
    date = models.DateField(_("対象日"))
    date_type = models.CharField(_("勤務状態"), max_length=20, choices=DateType.choices, default=DateType.PRESENT)
    note = models.CharField(_("備考"), max_length=255, blank=True)

    clock_in_time = models.DateTimeField(_("出勤日時"), null=True, blank=True)
    clock_out_time = models.DateTimeField(_("退勤日時"), null=True, blank=True)
    has_lunch_break = models.BooleanField(_("ランチ休憩有無"), default=True)
    has_break1 = models.BooleanField(_("休憩1有無"), default=True)
    has_break2 = models.BooleanField(_("休憩2有無"), default=True)
    has_break3 = models.BooleanField(_("休憩3有無"), default=True)
    has_break4 = models.BooleanField(_("休憩4有無"), default=True)
    has_break5 = models.BooleanField(_("休憩5有無"), default=True)
    other_break_minutes = models.PositiveIntegerField(_("その他休憩時間（分）"), default=0)

    class Meta:
        db_table = "attendance_daily"
        verbose_name = _("日次勤怠")
        verbose_name_plural = _("日次勤怠一覧")
        unique_together = ("monthly_attendance", "date")  # 1人1日1レコードに制限
        ordering = ("-date", "monthly_attendance__member")

    def get_work_pattern(self):
        """勤務形態を返す"""
        if self.work_pattern:
            return self.work_pattern
        elif self.monthly_attendance.work_pattern:
            return self.monthly_attendance.work_pattern
        else:
            work_pattern = (
                WorkPattern.objects.all()
                .annotate(custom_order=Case(When(name="所定", then=Value(1)), default=Value(2), output_field=IntegerField()))
                .order_by("custom_order", "start_time")
            ).first()
            if work_pattern:
                return work_pattern
            else:
                raise ValueError("勤務形態が設定されていません。")

    def standard_start_time(self):
        """標準勤務開始時刻を返す（半休などを考慮して計算）"""
        work_pattern = self.get_work_pattern()
        start_time = work_pattern.start_time
        if self.date_type == self.DateType.MORNING_PAID_LEAVE:
            # 午前半休の勤務開始時刻を設定
            start_time = work_pattern.start_time + timedelta(minutes=HALF_DAY_MINUTES)
        return start_time

    def standard_end_time(self):
        """標準勤務終了時刻を返す（半休などを考慮して計算）"""
        work_pattern = self.get_work_pattern()
        end_time = work_pattern.end_time
        if self.date_type == self.DateType.AFTERNOON_PAID_LEAVE:
            # 午後半休の標準勤務終了時刻を設定
            end_time = work_pattern.start_time + timedelta(minutes=HALF_DAY_MINUTES)
        return end_time

    def is_present(self):
        """出勤状態かどうかを返す"""
        return (
            self.date_type == self.DateType.PRESENT
            or self.date_type == self.DateType.MORNING_PAID_LEAVE
            or self.date_type == self.DateType.AFTERNOON_PAID_LEAVE
        )

    def get_late_minutes(self):
        """遅刻時間を分単位で返す"""
        if self.is_present() and self.clock_in_time.time() > self.standard_start_time():
            return get_duration_in_minutes(self.standard_start_time(), self.clock_in_time.time())
        return 0

    def get_early_leave_minutes(self):
        """早退時間を分単位で返す"""
        if self.is_present() and self.clock_out_time and self.clock_out_time.time() < self.standard_end_time():
            return get_duration_in_minutes(self.clock_out_time.time(), self.standard_end_time())
        return 0

    def lunch_break_minutes(self):
        """ランチ休憩時間を分単位で返す"""
        work_pattern = self.get_work_pattern()
        if self.has_lunch_break and self.clock_in_time and self.clock_out_time and self.clock_in_time <= work_pattern.lunch_break_start_time:
            if self.clock_out_time >= work_pattern.lunch_break_end_time:
                minutes = work_pattern.lunch_break_duration()
            else:
                minutes = get_duration_in_minutes(work_pattern.lunch_break_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break1_minutes(self):
        """休憩1時間を分単位で返す"""
        work_pattern = self.get_work_pattern()
        if self.has_break1 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= work_pattern.break1_start_time:
            if self.clock_out_time >= work_pattern.break1_end_time:
                minutes = work_pattern.break1_duration()
            else:
                minutes = get_duration_in_minutes(work_pattern.break1_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break2_minutes(self):
        """休憩2時間を分単位で返す"""
        work_pattern = self.get_work_pattern()
        if self.has_break2 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= work_pattern.break2_start_time:
            if self.clock_out_time >= work_pattern.break2_end_time:
                minutes = work_pattern.break2_duration()
            else:
                minutes = get_duration_in_minutes(work_pattern.break2_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break3_minutes(self):
        """休憩3時間を分単位で返す"""
        work_pattern = self.get_work_pattern()
        if self.has_break3 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= work_pattern.break3_start_time:
            if self.clock_out_time >= work_pattern.break3_end_time:
                minutes = work_pattern.break3_duration()
            else:
                minutes = get_duration_in_minutes(work_pattern.break3_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break4_minutes(self):
        """休憩4時間を分単位で返す"""
        work_pattern = self.get_work_pattern()
        if self.has_break4 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= work_pattern.break4_start_time:
            if self.clock_out_time >= work_pattern.break4_end_time:
                minutes = work_pattern.break4_duration()
            else:
                minutes = get_duration_in_minutes(work_pattern.break4_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break5_minutes(self):
        """休憩5時間を分単位で返す"""
        work_pattern = self.get_work_pattern()
        if self.has_break5 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= work_pattern.break5_start_time:
            if self.clock_out_time >= work_pattern.break5_end_time:
                minutes = work_pattern.break5_duration()
            else:
                minutes = get_duration_in_minutes(work_pattern.break5_start_time, self.clock_out_time.time())
            return minutes
        return 0

    # 管理画面や画面表示用に「○時間×分」で取得するヘルパーメソッド
    def actual_work_minutes(self):
        """実労働時間を分単位で返す"""
        if self.clock_in_time and self.clock_out_time:
            total_work_minutes = get_duration_in_minutes(self.clock_in_time.time(), self.clock_out_time.time())
            total_break_minutes = (
                self.lunch_break_minutes()
                + self.break1_minutes()
                + self.break2_minutes()
                + self.break3_minutes()
                + self.break4_minutes()
                + self.break5_minutes()
                + self.other_break_minutes
            )
            return max(total_work_minutes - total_break_minutes, 0)
        return 0

    def display_work_time(self):
        """実労働時間を「○時間×分」の形式で返す"""
        hours = self.actual_work_minutes // 60
        minutes = self.actual_work_minutes % 60
        return f"{hours}時間{minutes}分"

    def overtime_minutes(self):
        """残業時間を分単位で返す"""
        if self.clock_in_time and self.clock_out_time:
            actual_work_minutes = self.actual_work_minutes()
            standard_work_minutes = get_duration_in_minutes(self.standard_start_time(), self.standard_end_time())
            return max(actual_work_minutes - standard_work_minutes, 0)
        return 0

    def display_overtime(self):
        """残業時間を「○時間×分」の形式で返す"""
        hours = self.overtime_minutes() // 60
        minutes = self.overtime_minutes() % 60
        return f"{hours}時間{minutes}分"

    def night_work_minutes(self):
        """深夜労働時間を分単位で返す"""
        if self.clock_in_time and self.clock_out_time:
            # 深夜労働時間の計算
            night_work_start = datetime.combine(self.date, NIGHT_standard_start_time)
            night_work_end = datetime.combine(self.date + timedelta(days=1), NIGHT_standard_end_time)

            # 出勤・退勤時間をdatetimeに変換
            clock_in_datetime = self.clock_in_time
            clock_out_datetime = self.clock_out_time

            # 深夜労働時間の重なり部分を計算
            overlap_start = max(clock_in_datetime, night_work_start)
            overlap_end = min(clock_out_datetime, night_work_end)

            if overlap_start < overlap_end:
                return (overlap_end - overlap_start).seconds // 60
        return 0

    def display_night_work_time(self):
        """深夜労働時間を「○時間×分」の形式で返す"""
        hours = self.night_work_minutes() // 60
        minutes = self.night_work_minutes() % 60
        return f"{hours}時間{minutes}分"

    display_work_time.short_description = "実労働時間"
    display_overtime.short_description = "残業時間"
    display_night_work_time.short_description = "深夜労働時間"
