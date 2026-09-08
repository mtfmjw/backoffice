from django.contrib import admin

from backoffice.admin import admin_site
from common.admin.base import RowScopedBaseModelAdmin
from kintai.models.paid_leave import PaidLeave


@admin.register(PaidLeave, site=admin_site)
class PaidLeaveAdmin(RowScopedBaseModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        readonly_fields.extend(["member", "year", "acquired_days"])
        if obj and not request.user.member.is_attendance_management_staff:
            readonly_fields.append("remaining_days")
        return readonly_fields
