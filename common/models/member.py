from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import BaseModel
from common.models.organization import Organization
from common.models.work_pattern import WorkPattern


class Member(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member", verbose_name=_("Employee Number"))
    email = models.EmailField(verbose_name=_("Email address"), blank=True, null=True, unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="members", verbose_name=_("Belongs to")
    )
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True)
    manager_flag = models.BooleanField(default=False, verbose_name=_("Manager Flag"))

    class Meta:
        db_table = "member"
        verbose_name = _("Member")
        verbose_name_plural = _("Members")

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name} ({self.user.username})"
