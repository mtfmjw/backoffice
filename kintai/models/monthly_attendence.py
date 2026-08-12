from datetime import time

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models import Member, WorkPattern
from common.models.base import BaseModel

NIGHT_START_TIME = time(22, 0)
NIGHT_END_TIME = time(5, 0)
HALF_DAY_MINUTES = 180  # 半日休暇の時間（分）


class MonthlyAttendance(BaseModel):
    """月次勤怠テーブル（1人1月あたりの確定データ）"""

    class ApproveStatus(models.IntegerChoices):
        ENTRY = 0, _("入力中")
        APPLYED = 1, _("申請済")
        APPROVED = 2, _("承認済")
        REJECTED = 3, _("却下")
        CONFIRMED = 4, _("確定済")

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, related_name="attendance_records", verbose_name=_("社員"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("勤務パターン"))
    date = models.DateField(_("対象月"))  # 月次勤怠の対象月（1日固定）
    approve_status = models.CharField(_("状態"), max_length=2, choices=ApproveStatus.choices, default=ApproveStatus.ENTRY)
    actual_work_minutes = models.PositiveIntegerField(_("実労働時間"), null=True, blank=True)
    overtime_minutes = models.PositiveIntegerField(_("残業時間"), null=True, blank=True)
    night_work_minutes = models.PositiveIntegerField(_("深夜労働時間"), null=True, blank=True)
    worked_days = models.PositiveIntegerField(_("出勤日数"), null=True, blank=True)
    paid_leave_days = models.PositiveIntegerField(_("有休日数"), null=True, blank=True)  # 半休含めて
    note = models.CharField(_("備考"), max_length=255, null=True, blank=True)

    class Meta:
        db_table = "attendance_monthly"
        verbose_name = _("月次勤怠")
        verbose_name_plural = _("月次勤怠一覧")
        unique_together = ("member", "date")  # 1人1月1レコードに制限
        ordering = ("-date", "member")

    def __str__(self):
        return f"{self.member.user.last_name} {self.member.user.first_name}({self.member.user.username}) " + self.date.strftime("%Y年%m月")
