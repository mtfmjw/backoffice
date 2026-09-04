from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import Member, WorkPattern
from common.models.base import ApprovedBaseModel


class MonthlyAttendance(ApprovedBaseModel):
    """月次勤怠テーブル（1人1月あたりの確定データ）"""

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, related_name="attendance_records", verbose_name=_("OrganizationMember"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("Work Pattern"))
    month = models.DateField(_("Month"))
    # 勤怠集計結果を保存するフィールド
    actual_work_minutes = models.PositiveIntegerField(_("Actual Working Time"), default=0, null=True, blank=True)
    worked_days = models.FloatField(_("Days Worked"), default=0, null=True, blank=True)
    paid_leave_days = models.FloatField(_("Paid Leave Days"), default=0, null=True, blank=True)  # Including half-days
    standard_working_days = models.PositiveIntegerField(_("Standard Working Days"), default=0, null=True, blank=True)
    absence_days = models.PositiveIntegerField(_("Absence Days"), default=0, null=True, blank=True)
    early_leave_days = models.PositiveIntegerField(_("Early Leave Days"), default=0, null=True, blank=True)
    late_days = models.PositiveIntegerField(_("Late Days"), default=0, null=True, blank=True)
    overtime_125 = models.PositiveIntegerField(_("Overtime 1.25"), default=0, null=True, blank=True)  # 普通残業時間（1.25）
    overtime_150 = models.PositiveIntegerField(_("Overtime 1.50"), default=0, null=True, blank=True)  # 普通深夜残業時間（1.50）
    night_time_025 = models.PositiveIntegerField(_("Night Overtime 0.25"), default=0, null=True, blank=True)  # 深夜就業時間（0.25）
    off_day_125 = models.PositiveIntegerField(_("Off Day 1.25"), default=0, null=True, blank=True)  # 休日出勤時間（1.25）
    off_day_150 = models.PositiveIntegerField(_("Off Day 1.50"), default=0, null=True, blank=True)  # 休日深夜出勤時間（1.50）
    holiday_135 = models.PositiveIntegerField(_("Holiday 1.35"), default=0, null=True, blank=True)  # 法定休日出勤時間（1.35）
    holiday_160 = models.PositiveIntegerField(_("Holiday 1.60"), default=0, null=True, blank=True)  # 法定休日深夜出勤時間（1.60）

    class Meta:
        db_table = "attendance_monthly"
        verbose_name = _("Monthly Attendance")
        verbose_name_plural = _("Monthly Attendances")
        unique_together = ("member", "month")  # 1人1月1レコードに制限
        ordering = ("-month", "member")

    def __str__(self):
        return (
            f"{self.member.user.last_name} {self.member.user.first_name}({self.member.user.username}) "
            + self.month.strftime("%Y年%m月")
            + f" （{_('Work Pattern')}: {self.work_pattern.name if self.work_pattern else '-'})"
            + f" - {self.get_approve_status_display()}"
        )
