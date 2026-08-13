from datetime import datetime
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django.contrib import admin
from django.contrib.admin import SimpleListFilter, display
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin

from backoffice.admin import admin_site
from common.admin.base import BaseModelAdminMixin
from kintai.models import MonthlyAttendance


class MonthFilter(SimpleListFilter):
    title = "対象月"
    parameter_name = "month"

    def lookups(self, request, model_admin):
        current_first_day = localdate().replace(day=1)
        choices = []
        for i in range(1, -5, -1):
            m_date = current_first_day + relativedelta(months=i)
            val = m_date.strftime("%Y-%m")
            label = m_date.strftime("%Y年%m月")
            choices.append((val, label))
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        if value is None:
            return queryset
        try:
            year, month = map(int, value.split("-"))
            return queryset.filter(date__year=year, date__month=month)
        except (ValueError, AttributeError):
            return queryset


@admin.register(MonthlyAttendance, site=admin_site)
class MonthlyAttendanceAdmin(BaseModelAdminMixin, ImportExportModelAdmin):
    change_list_template = "kintai/monthly_attendance_change_list.html"
    list_display = (
        "member",
        "month",
        "belong",
        "approve_status",
        "actual_work_minutes",
        "overtime_minutes",
        "night_work_minutes",
        "worked_days",
        "paid_leave_days",
    ) + BaseModelAdminMixin.list_display
    search_fields = ("member__user__username", "member__user__last_name", "member__user__first_name", "member__organization__name")
    list_select_related = ("member", "work_pattern")
    list_filter = (MonthFilter, "approve_status") + BaseModelAdminMixin.list_filter
    readonly_fields = (
        "actual_work_minutes",
        "overtime_minutes",
        "night_work_minutes",
        "worked_days",
        "paid_leave_days",
    )

    @display(description="勤務月")
    def month(self, obj):
        return obj.date.strftime("%Y/%m")

    @display(description="所属")
    def belong(self, obj):
        return obj.member.organization.name

    def has_add_permission(self, request):
        return request.user.is_authenticated and hasattr(request.user, "member")

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # If your default filter kicks in when parameter is empty, fall back to default
        month_filtered = request.GET.get("month", localdate().strftime("%Y-%m"))

        # used internally to redirect users back to the filtered list view after saving an object
        extra_context["preserved_filters"] = f"?month={month_filtered}"

        # Inject custom query string for the Add URL
        extra_context["add_url_params"] = urlencode({"month": month_filtered})

        return super().changelist_view(request, extra_context=extra_context)

    def get_changeform_initial_data(self, request):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        return super().get_changeform_initial_data(request)

    def get_fieldsets(self, request, obj=None):
        return (
            (
                None,
                {
                    "fields": (
                        ("work_pattern", "approve_status"),
                        ("actual_work_minutes", "overtime_minutes", "night_work_minutes", "worked_days", "paid_leave_days"),
                    ),
                },
            ),
        )

    def add_view(self, request, form_url="", extra_context=None):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        member = request.user.member
        month_str = request.GET.get("month", localdate().strftime("%Y-%m"))
        first_day = datetime.strptime(month_str, "%Y-%m").date()  # noqa: DTZ007
        attendance = MonthlyAttendance.objects.filter(member=member, date=first_day).first()
        if attendance:
            attendance_id = attendance.id
        else:
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("""CALL create_monthly_attendance(%s, %s, %s, %s);""", [member.id, first_day, request.user.username, 0])
                attendance_id = cursor.fetchone()[0]

        return redirect(reverse("admin:kintai_monthlyattendance_change", args=(attendance_id,)))

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save_and_add_another"] = False
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)
