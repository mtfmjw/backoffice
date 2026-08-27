from django.db import models
from django.utils.translation import gettext_lazy as _

from common.middleware import get_current_user


class AuthorizedModelMixin:
    """This mixin provides methods to check if a user is authorized to perform actions on a model instance."""

    @classmethod
    def is_authorized(cls, login_user):
        """Only authenticated users with a member profile are authorized to access this model instance."""
        return login_user.is_authenticated and getattr(login_user, "member", None) is not None

    def is_editable_by(self, login_user):
        """Check if the record is editable by the given user."""
        return self.is_authorized(login_user)

    def is_deletable_by(self, login_user):
        """Check if the record is deletable by the given user."""
        return self.is_editable_by(login_user)


class BaseModel(AuthorizedModelMixin, models.Model):
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


class MemberScopedBaseModel(BaseModel):
    """This mixin provides methods to check if a user with a member profile can access a model instance."""

    class Meta:
        abstract = True

    @classmethod
    def is_authorized(cls, login_user):
        """Access is restricted to company executives and members assigned to an organization."""
        if not super().is_authorized(login_user):
            return False

        if login_user.member.organization is None:
            return login_user.member.is_company_executive()
        return True

    def is_editable_by(self, login_user):
        """Check if the record is editable by the given user."""
        if not super().is_editable_by(login_user):
            return False

        # ログインユーザーは自分が所有するモデルを編集可能
        if login_user.member == self.member:
            return True

        # ログインユーザーが組織長の場合、自分の所属組織の下部組織に所属するモデルを編集可能
        return (
            login_user.member.is_organization_manager() and login_user.member.organization in self.member.organization.get_ancestor_organizations()
        )

    @classmethod
    def is_all_organizations_accessible(cls, login_user):
        """Check if the member can view all organizations."""
        return cls.is_authorized(login_user) and login_user.member.is_company_executive()

    @classmethod
    def get_accessible_top_organization(cls, login_user):
        """Get the highest level organization that the member can access."""
        if not cls.is_authorized(login_user):
            return None
        return login_user.member.organization if login_user.member.is_organization_manager() else None
