from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import Member, RowScopedBaseModel, WorkPattern
from kintai.const import ApproveStatus, DateStatus


class MonthlyAttendance(RowScopedBaseModel):
    """月次勤怠テーブル（1人1月あたりの確定データ）"""

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, related_name="attendance_records", verbose_name=_("OrganizationMember"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("Work Pattern"))
    month = models.DateField(_("Month"))
    approve_status = models.IntegerField(_("Approve Status"), choices=ApproveStatus.choices, default=ApproveStatus.DRAFT)
    # 承認・確定情報
    applied_by = models.CharField(_("Applied by"), max_length=100, null=True, blank=True)
    applied_at = models.DateTimeField(_("Applied at"), null=True, blank=True)
    approved_by = models.CharField(_("Approved by"), max_length=100, null=True, blank=True)
    approved_at = models.DateTimeField(_("Approved at"), null=True, blank=True)
    confirmed_by = models.CharField(_("Confirmed by"), max_length=100, null=True, blank=True)
    confirmed_at = models.DateTimeField(_("Confirmed at"), null=True, blank=True)
    note = models.CharField(_("Note"), max_length=255, null=True, blank=True)
    # 勤怠集計結果を保存するフィールド
    actual_work_minutes = models.PositiveIntegerField(_("Actual Working Time"), default=0, null=True, blank=True)
    overtime_minutes = models.PositiveIntegerField(_("Overtime"), default=0, null=True, blank=True)
    night_work_minutes = models.PositiveIntegerField(_("Night Working Time"), default=0, null=True, blank=True)
    worked_days = models.FloatField(_("Days Worked"), default=0, null=True, blank=True)
    paid_leave_days = models.FloatField(_("Paid Leave Days"), default=0, null=True, blank=True)  # Including half-days
    standard_working_days = models.PositiveIntegerField(_("Standard Working Days"), default=0, null=True, blank=True)
    absence_days = models.PositiveIntegerField(_("Absence Days"), default=0, null=True, blank=True)
    early_leave_days = models.PositiveIntegerField(_("Early Leave Days"), default=0, null=True, blank=True)
    late_days = models.PositiveIntegerField(_("Late Days"), default=0, null=True, blank=True)
    total_absence_minutes = models.PositiveIntegerField(_("Total Absence Time"), default=0, null=True, blank=True)

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
        """The daily attendance records are only editable by the member themselves when the record is in DRAFT or REJECTED status."""
        if self.approve_status in [ApproveStatus.DRAFT, ApproveStatus.REJECTED]:
            return login_user.member == self.member
        else:
            return False

    def is_deletable_by(self, login_user):
        """Check if the record is deletable by the given user."""
        return (
            self.is_editable_by(login_user)
            and self.member == login_user.member
            and self.approve_status in [ApproveStatus.DRAFT, ApproveStatus.REJECTED]
        )

    def is_approvable_by(self, login_user):
        """Check if the record is approvable by the given user."""
        return (
            login_user.member.is_organization_manager() or login_user.member.is_company_executive()
        ) and self.approve_status == ApproveStatus.APPLIED

    def is_confirmable_by(self, login_user):
        """Check if the record is confirmable by the given user."""
        return (
            login_user.member.is_attendance_management_staff() or login_user.member.is_company_executive()
        ) and self.approve_status == ApproveStatus.APPROVED

    @classmethod
    def is_all_organizations_accessible(cls, login_user):
        """Check if the model is accessible to all organizations."""
        return super().is_all_organizations_accessible(login_user) or login_user.member.is_attendance_management_staff()

    def update_derived_fields(self):
        """Update the aggregate fields of the monthly attendance record."""

        daily_records = self.daily_attendances.all()
        self.actual_work_minutes = sum(day_record.actual_work_minutes for day_record in daily_records)
        self.overtime_minutes = sum(day_record.overtime_minutes for day_record in daily_records)
        self.night_work_minutes = sum(day_record.night_work_minutes for day_record in daily_records)
        self.worked_days = sum(day_record.get_worked_days() for day_record in daily_records)
        self.paid_leave_days = sum(day_record.get_paid_leave_days() for day_record in daily_records)
        self.standard_working_days = sum(1 if day_record.is_work_day() else 0 for day_record in daily_records)
        self.absence_days = sum(1 if day_record.date_status == DateStatus.ABSENCE else 0 for day_record in daily_records)
        self.early_leave_days = sum(1 if (day_record.early_leave_minutes or 0) > 0 else 0 for day_record in daily_records)
        self.late_days = sum(1 if (day_record.late_minutes or 0) > 0 else 0 for day_record in daily_records)
        self.total_absence_minutes = sum(
            (day_record.early_leave_minutes or 0)
            + (day_record.late_minutes or 0)
            + (day_record.work_pattern.get_standard_work_minutes() if day_record.date_status == DateStatus.ABSENCE else 0)
            for day_record in daily_records
        )
        self.save(
            update_fields=[
                "actual_work_minutes",
                "overtime_minutes",
                "night_work_minutes",
                "worked_days",
                "paid_leave_days",
                "standard_working_days",
                "absence_days",
                "early_leave_days",
                "late_days",
                "total_absence_minutes",
            ]
        )
