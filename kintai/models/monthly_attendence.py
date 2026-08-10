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
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("勤務形態"))
    date = models.DateField(_("対象月"), help_text=_("対象月の1日を指定してください。例: 2023-01-01"))
    approve_status = models.CharField(_("処理状態"), max_length=20, choices=ApproveStatus.choices, default=ApproveStatus.ENTRY)
    actual_work_minutes = models.PositiveIntegerField(_("実労働時間（分）"), default=0)
    overtime_minutes = models.PositiveIntegerField(_("残業時間（分）"), default=0)
    night_work_minutes = models.PositiveIntegerField(_("深夜労働時間（分）"), default=0)
    note = models.CharField(_("備考"), max_length=255, blank=True)

    class Meta:
        db_table = "attendance_monthly"
        verbose_name = _("月次勤怠")
        verbose_name_plural = _("月次勤怠一覧")
        unique_together = ("member", "date")  # 1人1月1レコードに制限
        ordering = ("-date", "member")
