from datetime import datetime
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from backoffice.admin import admin_site
from common.admin.base import BaseModelAdmin
from kintai.models import MonthlyAttendance


class MonthlyFilter(SimpleListFilter):
    title = "対象月"
    parameter_name = "month"

    def lookups(self, request, model_admin):
        today = localdate()
        current_first = today.replace(day=1)
        choices = []
        for i in range(1, -5, -1):
            m_date = current_first + relativedelta(months=i)
            val = m_date.strftime("%Y-%m")
            label = m_date.strftime("%Y年%m月")
            choices.append((val, label))
        return choices

    def value(self):
        """
        1. Returns the selected option from URL parameter (?status=...).
        2. Fallback to 'active' as default when no parameter is present.
        """
        val = super().value()
        if val is None:
            today = timezone.localdate()
            current_month = f"{today.year}-{today.month}"
            return current_month  # default filter option
        return val

    def queryset(self, request, queryset):
        value = self.value()
        if value is None:
            today = timezone.localdate()
            return queryset.filter(date__year=today.year, date__month=today.month)
        try:
            year, month = map(int, value.split("-"))
            return queryset.filter(date__year=year, date__month=month)
        except (ValueError, AttributeError):
            return queryset

    def choices(self, changelist):
        """
        Override choices to strip out the default 'All' option.
        """
        # Call the parent generator to get all choices
        all_choices = list(super().choices(changelist))

        # The first item (index 0) in all_choices is always the 'All' link.
        # Returning all_choices[1:] strips it out.
        return all_choices[1:]


@admin.register(MonthlyAttendance, site=admin_site)
class MonthlyAttendanceAdmin(BaseModelAdmin):
    change_list_template = "kintai/monthly_attendance_change_list.html"
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
    list_filter = (MonthlyFilter, "approve_status") + BaseModelAdmin.list_filter
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

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # If your default filter kicks in when parameter is empty, fall back to default
        today = timezone.localdate()
        current_month = f"{today.year}-{today.month}"
        month_filter = request.GET.get("month", current_month)

        # used internally to redirect users back to the filtered list view after saving an object
        extra_context["preserved_filters"] = f"?month={month_filter}"

        # Inject custom query string for the Add URL
        extra_context["add_url_params"] = urlencode({"month": month_filter})

        return super().changelist_view(request, extra_context=extra_context)

    def get_changeform_initial_data(self, request):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        initial = super().get_changeform_initial_data(request)

        # Read filter choice passed from URL query parameters
        if "month" in request.GET:
            initial["month"] = request.GET.get("month")

        return initial

    def add_view(self, request, form_url="", extra_context=None):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        member = request.user.member
        month_str = request.GET.get("month")
        first_day = datetime.strptime(month_str, "%Y-%m").date()  # noqa: DTZ007
        attendance, created = MonthlyAttendance.objects.get_or_create(  # noqa: RUF059
            member=member,
            date=first_day,
            defaults={"member": member, "date": first_day},
        )

        return redirect(
            reverse(
                "admin:kintai_monthlyattendance_change",
                args=(attendance.pk,),
            )
        )
