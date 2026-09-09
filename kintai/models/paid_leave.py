from functools import cached_property

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models.base import RowScopedBaseModel
from common.models.member import Member


class PaidLeave(RowScopedBaseModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, verbose_name=_("Organization Member"), related_name="paid_leaves")
    valid_from = models.DateField(_("Valid From"))
    valid_till = models.DateField(_("Valid To"))
    acquired_days = models.FloatField(_("Acquired Days"), default=0)
    remaining_days = models.FloatField(_("Remaining Days"), default=0)

    class Meta:
        db_table = "paid_leave"
        unique_together = ("member", "valid_from")
        verbose_name = _("Paid Leave")
        verbose_name_plural = _("Paid Leaves")
        ordering = ("-valid_from",)

    @classmethod
    def is_authorized(cls, login_user):
        return super().is_authorized(login_user) or login_user.member.is_accounting_staff

    def is_editable_by(self, login_user):
        return login_user.member.is_accounting_staff

    def is_deletable_by(self, login_user):
        return False

    @classmethod
    def is_all_organizations_accessible(cls, login_user):
        return login_user.member.is_accounting_staff or super().is_all_organizations_accessible(login_user)

    @cached_property
    def available_days(self):
        today = timezone.localdate()
        all_remaining_days = PaidLeave.objects.filter(member=self.member, valid_from__lte=today, valid_till__gte=today).values_list(
            "remaining_days", flat=True
        )
        return sum(all_remaining_days)

    def update_remaining_days(self, taken_days, updated_by):
        if taken_days <= 0:
            return

        today = timezone.localdate()
        valid_paid_leaves = PaidLeave.objects.filter(member=self.member, valid_from__lte=today, valid_till__gte=today)
        for paid_leave in valid_paid_leaves:
            if paid_leave.remaining_days >= taken_days:
                paid_leave.remaining_days -= taken_days
                taken_days = 0
            else:
                taken_days -= paid_leave.remaining_days
                paid_leave.remaining_days = 0
            paid_leave.updated_by = updated_by
            paid_leave.save()
            if taken_days <= 0:
                break
