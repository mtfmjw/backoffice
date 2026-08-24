from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import BaseModel
from common.models.organization import Organization
from common.models.work_pattern import WorkPattern

# 会社経営層グループ
COMPANY_EXECUTIVE_GROUP = "経営管理グループ"

# 組織責任者グループ
ORGANIZATION_MANAGER_GROUP = "組織責任者グループ"

# superuserの代わりに権限を明示的に付与してシステム管理を行うグループ
SYSTEM_INFO_GROUP = "情シスグループ"

# 勤怠管理グループ
ATTENDANCE_MANAGEMENT_GROUP = "勤怠管理グループ"

# 営業グループ
SALES_GROUP = "営業グループ"


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

    def is_system_info_staff(self):
        return self.user.groups.filter(name=SYSTEM_INFO_GROUP).exists()

    def is_organization_manager(self):
        return self.user.groups.filter(name=ORGANIZATION_MANAGER_GROUP).exists()

    def is_attendance_management_staff(self):
        return self.user.groups.filter(name=ATTENDANCE_MANAGEMENT_GROUP).exists()

    def is_same_organization(self, other_member):
        """Check if the other member belongs to the same organization."""
        if not isinstance(other_member, Member) or self.organization is None or other_member.organization is None:
            return False

        return self.organization.is_same_organization(other_member.organization)

    def is_all_organizations_accessible(self):
        """Check if the member can view all organizations."""
        return self.is_system_info_staff() or self.is_company_executive()

    def is_editable_by(self, login_user):
        """Check if the record is editable by the given user."""
        if not login_user.is_authenticated or not hasattr(login_user, "member") or getattr(login_user, "member", None) is None:
            return False
        elif login_user.member.is_company_executive() or login_user.member.is_system_info_staff():
            return True
        elif login_user.member.organization is None:
            return False

        if login_user.member == self:
            return True

        if self.organization is None:
            return not self.is_company_executive()

        # ログインユーザーが組織長の場合、自分の所属組織の下部組織に所属するモデルを編集可能
        return login_user.member.is_organization_manager() and login_user.member.organization in self.organization.get_ancestor_organizations()
