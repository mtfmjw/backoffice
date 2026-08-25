from django.db import models
from django.utils.translation import gettext_lazy as _

from common.middleware import get_current_user


class AuthenticationModelMixin:
    """
    Modelインスタンスごとに編集と削除の権限を制限するためのメソッドを提供するミックスイン
    modelAdminのhas_change_permissionとhas_delete_permissionで使用することを想定
    has_add_permissionとhas_view_permissionはdjangoの仕組みをそのまま使用するため、ここでは定義しない
    """

    def is_editable_by(self, login_user):
        """Check if the record is editable by the given user."""
        # ログインユーザーによる判定
        if not login_user.is_authenticated or not hasattr(login_user, "member") or getattr(login_user, "member", None) is None:
            return False
        elif login_user.member.is_company_executive():
            return True
        elif login_user.member.organization is None:
            return False

        # アクセスする対象モデルによる判定
        if not hasattr(self, "member") or getattr(self, "member", None) is None:
            return True

        if self.member.organization is None:
            return not self.member.is_company_executive()

        # ログインユーザーは自分が所有するモデルを編集可能
        if login_user.member == self.member:
            return True

        # ログインユーザーが組織長の場合、自分の所属組織の下部組織に所属するモデルを編集可能
        return (
            login_user.member.is_organization_manager() and login_user.member.organization in self.member.organization.get_ancestor_organizations()
        )

    def is_deletable_by(self, login_user):
        """Check if the record is deletable by the given user."""
        return self.is_editable_by(login_user)


class BaseModel(models.Model):
    valid_flag = models.BooleanField(default=True, verbose_name=_("Valid"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    created_by = models.CharField(max_length=150, verbose_name=_("Created by"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    updated_by = models.CharField(max_length=150, verbose_name=_("Updated by"))

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user.get_username()
            self.updated_by = user.get_username()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.valid_flag = False
        self.save()
