from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import RowScopedBaseModel
from common.models.member import Member


class PaidLeave(RowScopedBaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, verbose_name=_("Organization Member"), related_name="paid_leaves")
    year = models.IntegerField(_("Year"))
    acquired_days = models.FloatField(_("Acquired Days"), default=0)
    remaining_days = models.FloatField(_("Remaining Days"), default=0)

    class Meta:
        db_table = "paid_leave"
        unique_together = ("member", "year")
        verbose_name = _("Paid Leave")
        verbose_name_plural = _("Paid Leaves")

    def is_editable_by(self, login_user):
        return self.member.is_attendance_management_staff

    @classmethod
    def is_all_organizations_accessible(cls, login_user):
        return login_user.member.is_attendance_management_staff or super().is_all_organizations_accessible(login_user)

    @classmethod
    def get_available_days(cls, member):
        all_remaining_days = PaidLeave.objects.filter(member=member, valid_flag=True).values_list("remaining_days", flat=True)
        return sum(all_remaining_days)

    def update_remaining_days(self, taken_days):
        if taken_days <= 0:
            return
        valid_paid_leaves = PaidLeave.objects.filter(member=self.member, valid_flag=True)
        for paid_leave in valid_paid_leaves:
            if paid_leave.remaining_days >= taken_days:
                paid_leave.remaining_days -= taken_days
                taken_days = 0
            else:
                taken_days -= paid_leave.remaining_days
                paid_leave.remaining_days = 0
            paid_leave.save()
            if taken_days == 0:
                break
