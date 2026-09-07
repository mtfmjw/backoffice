from common.const import ApproveStatus


class KintaiBaseModelMixin:
    """Base model mixin for Kintai models with common functionality."""

    def is_confirmable_by(self, login_user):
        """Check if the record is confirmable by the given user."""
        if self.is_authorized(login_user) and self.approve_status == ApproveStatus.APPROVED and login_user.member.is_attendance_management_staff:
            return True
        return super().is_confirmable_by(login_user)

    @classmethod
    def is_all_organizations_accessible(cls, login_user):
        """Check if the member can view all organizations."""
        if login_user.member.is_attendance_management_staff:
            return True

        return super().is_all_organizations_accessible(login_user)
