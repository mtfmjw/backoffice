from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import BaseModel
from common.models.organization import Organization
from common.models.work_pattern import WorkPattern

# 会社経営層グループ
COMPANY_EXECUTIVE_GROUP = "経営幹部グループ"

# 組織責任者グループ
ORGANIZATION_MANAGER_GROUP = "組織責任者グループ"

# superuserの代わりに権限を明示的に付与してシステム管理を行うグループ
SYSTEM_INFO_GROUP = "情シスグループ"

# 勤怠管理グループ
KINTAI_STAFF_GROUP = "勤怠管理グループ"


class Member(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member", verbose_name=_("Employee Number"))
    email = models.EmailField(verbose_name=_("Email address"), blank=True, null=True, unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="members", verbose_name=_("Belongs to")
    )
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("Work Pattern"))

    class Meta:
        db_table = "member"
        verbose_name = _("Member")
        verbose_name_plural = _("Members")

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name} ({self.user.username})"

    def is_company_executive(self):
        return self.user.groups.filter(name=COMPANY_EXECUTIVE_GROUP).exists()

    def is_organization_manager(self):
        return self.user.groups.filter(name=ORGANIZATION_MANAGER_GROUP).exists()

    def is_system_info_staff(self):
        return self.user.groups.filter(name=SYSTEM_INFO_GROUP).exists()

    def is_kintai_staff(self):
        return self.user.groups.filter(name=KINTAI_STAFF_GROUP).exists()
