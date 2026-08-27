from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import BaseModel, Member, OrgScopedBaseModel, WorkPattern


class MonthlyAttendance(OrgScopedBaseModel, BaseModel):
    """月次勤怠テーブル（1人1月あたりの確定データ）"""

    class ApproveStatus(models.IntegerChoices):
        DRAFT = 0, _("Draft")  # 入力中
        APPLIED = 1, _("Applied")  # 申請済
        APPROVED = 2, _("Approved")  # 承認済
        REJECTED = 3, _("Rejected")  # 却下
        FINALIZED = 4, _("Finalized")  # 確定済

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, related_name="attendance_records", verbose_name=_("OrganizationMember"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("Work Pattern"))
    month = models.DateField(_("Month"))
    approve_status = models.IntegerField(_("Approve Status"), choices=ApproveStatus.choices, default=ApproveStatus.DRAFT)
    note = models.CharField(_("Note"), max_length=255, null=True, blank=True)
    # 勤怠集計結果を保存するフィールド
    actual_work_minutes = models.PositiveIntegerField(_("Actual Working Time"), null=True, blank=True)
    overtime_minutes = models.PositiveIntegerField(_("Overtime"), null=True, blank=True)
    night_work_minutes = models.PositiveIntegerField(_("Night Working Time"), null=True, blank=True)
    worked_days = models.PositiveIntegerField(_("Days Worked"), null=True, blank=True)
    paid_leave_days = models.FloatField(_("Paid Leave Days"), null=True, blank=True)  # Including half-days
    standard_working_days = models.PositiveIntegerField(_("Standard Working Days"), null=True, blank=True)
    absence_days = models.FloatField(_("Absence Days"), null=True, blank=True)
    early_leave_days = models.FloatField(_("Early Leave Days"), null=True, blank=True)
    late_days = models.FloatField(_("Late Days"), null=True, blank=True)
    total_absence_minutes = models.PositiveIntegerField(_("Total Absence Time"), null=True, blank=True)

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

    def is_editable_by(self, login_user):
        """Check if the daily attendance records associated with this monthly attendance are editable by the given user."""
        is_editable = super().is_editable_by(login_user) or login_user.member.is_attendance_management_staff()

        if self.approve_status in [self.ApproveStatus.DRAFT, self.ApproveStatus.REJECTED]:
            return is_editable and (login_user.member == self.member)
        else:
            return False

    def is_deletable_by(self, login_user):
        """Check if the record is deletable by the given user."""
        return (
            self.is_editable_by(login_user)
            and self.member == login_user.member
            and self.approve_status in [self.ApproveStatus.DRAFT, self.ApproveStatus.REJECTED]
        )
