class KintaiBaseModelMixin:
    """Base model mixin for Kintai models with common functionality."""

    @classmethod
    def is_all_organizations_accessible(cls, login_user):
        """Check if the member can view all organizations."""
        if login_user.member.is_attendance_management_staff:
            return True

        return super().is_all_organizations_accessible(login_user)
