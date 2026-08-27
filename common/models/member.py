from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.const import ATTENDANCE_MANAGEMENT_GROUP, COMPANY_EXECUTIVE_GROUP, ORGANIZATION_MANAGER_GROUP, SYSTEM_INFO_GROUP

from .base import OrgScopedBaseModel
from .organization import Organization
from .work_pattern import WorkPattern


class Member(OrgScopedBaseModel):
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

    @classmethod
    def is_authorized(cls, login_user):
        """Only authenticated users with a member profile are authorized to access this model instance."""
        # If the user belongs to the SYSTEM_INFO_GROUP, they are authorized regardless of whether they have a member profile.
        if login_user.groups.filter(name=SYSTEM_INFO_GROUP).exists():
            return True

        return login_user.is_authenticated and getattr(login_user, "member", None) is not None

    def is_editable_by(self, login_user):
        """Check if the record is editable by the given user."""
        # If the user belongs to the SYSTEM_INFO_GROUP, they are authorized regardless of whether they have a member profile.
        if login_user.groups.filter(name=SYSTEM_INFO_GROUP).exists():
            return True

        # ログインユーザーは自分が所有するモデルを編集可能
        if login_user.member == self:
            return True

        if getattr(self, "organization", None) is None:
            return False

        # ログインユーザーが組織長の場合、自分の所属組織の下部組織に所属するモデルを編集可能
        return login_user.member.is_organization_manager() and login_user.member.organization in self.organization.get_ancestor_organizations()

    @classmethod
    def is_all_organizations_accessible(cls, login_user):
        return True
