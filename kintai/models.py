from datetime import timedelta

from django.db import models
from django.utils.timezone import datetime, localdate
from django.utils.translation import gettext_lazy as _

from common.models import Member

NIGHT_WORK_START_TIME = datetime.strptime("22:00", "%H:%M").time()
NIGHT_WORK_END_TIME = datetime.strptime("05:00", "%H:%M").time()
HALF_DAY_MINUTES = 180  # 半日休暇の時間（分）


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
    def get_holiday_type(day: date) -> str | None:
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
    def get_holiday_type_display(day: date) -> str:
        """祝日・休日の区分を返す"""
        return Holiday.get_holiday_type(day) and Holiday.Category(Holiday.get_holiday_type(day)).label or ""


def get_duration_in_minutes(start_time, end_time):
    """2つの時刻の差を分単位で返す"""
    base_start_date = localdate()
    if end_time < start_time:
        # 日を跨ぐ場合は、end_timeを翌日に設定
        base_end_date = base_start_date + timedelta(days=1)
    else:
        base_end_date = base_start_date

    return (datetime.combine(base_end_date, end_time) - datetime.combine(base_start_date, start_time)).seconds // 60


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


class AttendanceRecord(models.Model):
    """日次勤怠テーブル（1人1日あたりの確定データ）"""

    class DateType(models.IntegerChoices):
        PRESENT = 0, _("出勤")
        ABSENT = 1, _("欠勤")
        MORNING_PAID_LEAVE = 2, _("午前半休")
        AFTERNOON_PAID_LEAVE = 3, _("午後半休")
        PAID_LEAVE = 4, _("有休")
        SPECIAL_LEAVE = 5, _("特別休暇")
        HOLIDAY = 6, _("休日")

    class ApproveStatus(models.IntegerChoices):
        ENTRY = 0, _("入力中")
        APPLYED = 1, _("申請済")
        APPROVED = 2, _("承認済")
        REJECTED = 3, _("却下")
        CONFIRMED = 4, _("確定済")

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, related_name="attendance_records", verbose_name=_("社員"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("勤務形態"))
    date = models.DateField(_("対象日"))
    date_type = models.CharField(_("勤務状態"), max_length=20, choices=DateType.choices, default=DateType.PRESENT)
    approve_status = models.CharField(_("処理状態"), max_length=20, choices=ApproveStatus.choices, default=ApproveStatus.ENTRY)
    reject_reason = models.CharField(_("却下理由"), max_length=255, blank=True)
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

    # 時間計算は「分単位（整数）」で保持
    # total_break_minutes = models.PositiveIntegerField(_("休憩時間（分）"), default=0)
    # actual_work_minutes = models.PositiveIntegerField(_("実労働時間（分）"), default=0)
    # overtime_minutes = models.PositiveIntegerField(_("残業時間（分）"), default=0)
    # night_work_minutes = models.PositiveIntegerField(_("深夜労働時間（分）"), default=0)

    class Meta:
        db_table = "attendance_record"
        verbose_name = _("日次勤怠")
        verbose_name_plural = _("日次勤怠一覧")
        unique_together = ("member", "date")  # 1人1日1レコードに制限
        ordering = ("-date", "member")

    def lunch_break_minutes(self):
        """ランチ休憩時間を分単位で返す"""
        if self.has_lunch_break and self.clock_in_time and self.clock_out_time and self.clock_in_time <= self.work_pattern.lunch_break_start_time:
            if self.clock_out_time >= self.work_pattern.lunch_break_end_time:
                minutes = self.work_pattern.lunch_break_duration()
            else:
                minutes = get_duration_in_minutes(self.work_pattern.lunch_break_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break1_minutes(self):
        """休憩1時間を分単位で返す"""
        if self.has_break1 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= self.work_pattern.break1_start_time:
            if self.clock_out_time >= self.work_pattern.break1_end_time:
                minutes = self.work_pattern.break1_duration()
            else:
                minutes = get_duration_in_minutes(self.work_pattern.break1_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break2_minutes(self):
        """休憩2時間を分単位で返す"""
        if self.has_break2 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= self.work_pattern.break2_start_time:
            if self.clock_out_time >= self.work_pattern.break2_end_time:
                minutes = self.work_pattern.break2_duration()
            else:
                minutes = get_duration_in_minutes(self.work_pattern.break2_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break3_minutes(self):
        """休憩3時間を分単位で返す"""
        if self.has_break3 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= self.work_pattern.break3_start_time:
            if self.clock_out_time >= self.work_pattern.break3_end_time:
                minutes = self.work_pattern.break3_duration()
            else:
                minutes = get_duration_in_minutes(self.work_pattern.break3_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break4_minutes(self):
        """休憩4時間を分単位で返す"""
        if self.has_break4 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= self.work_pattern.break4_start_time:
            if self.clock_out_time >= self.work_pattern.break4_end_time:
                minutes = self.work_pattern.break4_duration()
            else:
                minutes = get_duration_in_minutes(self.work_pattern.break4_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def break5_minutes(self):
        """休憩5時間を分単位で返す"""
        if self.has_break5 and self.clock_in_time and self.clock_out_time and self.clock_in_time <= self.work_pattern.break5_start_time:
            if self.clock_out_time >= self.work_pattern.break5_end_time:
                minutes = self.work_pattern.break5_duration()
            else:
                minutes = get_duration_in_minutes(self.work_pattern.break5_start_time, self.clock_out_time.time())
            return minutes
        return 0

    def standard_start_time(self):
        """標準勤務開始時刻を返す"""
        start_time = self.work_pattern.start_time
        if self.date_type == self.DateType.AFTERNOON_PAID_LEAVE:
            # 午後半休の場合は、標準勤務開始時刻を休憩終了時刻に設定
            start_time = self.work_pattern.start_time + timedelta(minutes=HALF_DAY_MINUTES)
            if (
                start_time > self.work_pattern.lunch_break_end_time
                and self.clock_in_time
                and self.clock_in_time.time() <= self.work_pattern.lunch_break_end_time
            ):
                # 半日休暇の時間が勤務時間を超える場合は、標準勤務開始時刻を標準勤務終了時刻に設定
                start_time = self.work_pattern.lunch_break_end_time
        return start_time

    def standard_end_time(self):
        """標準勤務終了時刻を返す"""
        end_time = self.work_pattern.end_time
        if self.date_type == self.DateType.MORNING_PAID_LEAVE:
            # 午前半休の場合は、標準勤務終了時刻を休憩開始時刻に設定
            end_time = self.work_pattern.start_time + timedelta(minutes=HALF_DAY_MINUTES)
        return end_time

    def is_late(self):
        """遅刻かどうかを判定する"""
        return self.clock_in_time and self.clock_in_time.time() > self.standard_start_time()

    def is_early_leave(self):
        """早退かどうかを判定する"""
        return self.clock_out_time and self.clock_out_time.time() < self.standard_end_time()

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
            night_work_start = datetime.combine(self.date, NIGHT_WORK_START_TIME)
            night_work_end = datetime.combine(self.date + timedelta(days=1), NIGHT_WORK_END_TIME)

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
