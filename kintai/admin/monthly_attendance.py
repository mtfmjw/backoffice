from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from backoffice.admin import admin_site
from common.admin.base import BaseModelAdmin
from kintai.models import MonthlyAttendance


@admin.register(MonthlyAttendance, site=admin_site)
class MonthlyAttendanceAdmin(BaseModelAdmin):
    list_display = (
        "member",
        "work_pattern",
        "date",
        "approve_status",
        "actual_work_minutes",
        "overtime_minutes",
        "night_work_minutes",
        "worked_days",
        "paid_leave_days",
    ) + BaseModelAdmin.list_display
    search_fields = ("member__code", "member__name")
    list_select_related = ("member", "work_pattern")
    readonly_fields = ("member", "approve_status") + BaseModelAdmin.readonly_fields
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("date", "approve_status"),
                    ("member", "work_pattern"),
                    ("actual_work_minutes", "overtime_minutes", "night_work_minutes", "worked_days", "paid_leave_days"),
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return request.user.is_authenticated and hasattr(request.user, "member")

    def get_changeform_initial_data(self, request):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        return {"member": request.user.member}
