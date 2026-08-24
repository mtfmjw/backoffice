import datetime
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter, display
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.forms import TextInput
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin

from backoffice.admin import admin_site
from common.admin.base import BaseModelAdminMixin, OrganizationFilterMixin
from common.models import WorkPattern
from common.utils import minutes2str
from kintai.models import DailyAttendance, MonthlyAttendance

from .daily_attendance import DailyAttendanceInline


class MonthFilter(SimpleListFilter):
    title = _("Month")
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
            return queryset.filter(month__year=year, month__month=month)
        except (ValueError, AttributeError):
            return queryset


class MonthlyAttendanceForm(forms.ModelForm):
    note = forms.CharField(
        label=_("Note"),
        widget=TextInput(
            attrs={
                "placeholder": _("昼間不在は[05:00~22:00]、夜間不在は[22:00~翌05:00]期間中期間中の標準休憩以外の不在時間があれば入力してください。")
            }
        ),
        required=False,
    )

    class Meta:
        model = MonthlyAttendance
        fields = "__all__"


@admin.register(MonthlyAttendance, site=admin_site)
class MonthlyAttendanceAdmin(BaseModelAdminMixin, OrganizationFilterMixin, ImportExportModelAdmin):
    form = MonthlyAttendanceForm
    # change_list_template = "kintai/monthly_attendance_change_list.html"
    # change_form_template = "kintai/monthly_attendance_change_form.html"
    list_display = (
        "member",
        "display_month",
        "belong",
        "approve_status",
        "display_worked_days",
        "display_working_time",
        "display_overtime",
        "display_night_working_time",
        "display_paid_leave_days",
        "absence_days",
        "early_leave_days",
        "late_days",
        "display_total_absence_minutes",
    ) + BaseModelAdminMixin.list_display
    search_fields = ("member__user__username", "member__user__last_name", "member__user__first_name", "member__organization__name")
    list_select_related = ("member", "work_pattern")
    list_filter = (MonthFilter, "approve_status") + BaseModelAdminMixin.list_filter
    readonly_fields = (
        "display_worked_days",
        "display_working_time",
        "display_overtime",
        "display_night_working_time",
        "display_paid_leave_days",
    )
    inlines = (DailyAttendanceInline,)

    @display(description=_("Month"))
    def display_month(self, obj) -> str:
        return obj.month.strftime("%Y/%m")

    @display(description=_("Belong To"))
    def belong(self, obj) -> str:
        if not obj.member or not obj.member.organization:
            return "-"
        return obj.member.organization.name

    @display(description=_("Days Worked"))
    def display_worked_days(self, obj) -> str:
        if not obj or not obj.month:
            return ""

        worked_days_val = obj.worked_days or 0
        return f"{worked_days_val}/{obj.standard_working_days}日" if obj.standard_working_days is not None else ""

    @display(description=_("Actual Working Time"))
    def display_working_time(self, obj) -> str:
        return minutes2str(obj.actual_work_minutes)

    @display(description=_("Overtime"))
    def display_overtime(self, obj) -> str:
        return minutes2str(obj.overtime_minutes)

    @display(description=_("Night Working Time"))
    def display_night_working_time(self, obj) -> str:
        return minutes2str(obj.night_work_minutes)

    @display(description=_("Paid Leave Days"))
    def display_paid_leave_days(self, obj) -> str:
        return f"{obj.paid_leave_days:.1f}日" if obj.paid_leave_days is not None else ""

    @display(description=_("Total Absence Time"))
    def display_total_absence_minutes(self, obj) -> str:
        return minutes2str(obj.total_absence_minutes)

    def has_add_permission(self, request):
        return request.user.is_authenticated and hasattr(request.user, "member")

    def has_change_permission(self, request, obj=None):
        return super().is_available_member(request)
        # return request.user.is_authenticated and hasattr(request.user, "member")

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
                    "fields": ("note",),
                },
            ),
        )

    def add_view(self, request, form_url="", extra_context=None):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        member = request.user.member
        month_str = request.GET.get("month", localdate().strftime("%Y-%m"))
        first_day = datetime.datetime.strptime(month_str, "%Y-%m").date()  # noqa: DTZ007
        attendance = MonthlyAttendance.objects.filter(member=member, month=first_day).first()
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

        extra_context["worked_days_label"] = _("Days Worked")
        extra_context["actual_working_time_label"] = _("Actual Working Time")
        extra_context["overtime_label"] = _("Overtime")
        extra_context["night_working_time_label"] = _("Night Working Time")
        extra_context["paid_leave_days_label"] = _("Paid Leave Days")
        extra_context["absence_days_label"] = _("Absence Days")
        extra_context["early_leave_days_label"] = _("Early Leave Days")
        extra_context["late_days_label"] = _("Late Days")
        extra_context["total_absence_time_label"] = _("Total Absence Time")

        if object_id is not None:
            obj = self.get_object(request, object_id)
            extra_context["worked_days"] = self.display_worked_days(obj)
            extra_context["actual_working_time"] = self.display_working_time(obj)
            extra_context["overtime"] = self.display_overtime(obj)
            extra_context["night_working_time"] = self.display_night_working_time(obj)
            extra_context["paid_leave_days"] = self.display_paid_leave_days(obj)
            extra_context["absence_days"] = f"{obj.absence_days}回" if obj.absence_days is not None else ""
            extra_context["early_leave_days"] = f"{obj.early_leave_days}回" if obj.early_leave_days is not None else ""
            extra_context["late_days"] = f"{obj.late_days}回" if obj.late_days is not None else ""
            extra_context["total_absence_time"] = self.display_total_absence_minutes(obj)
            work_pattern = obj.work_pattern

            obj = self.get_object(request, object_id)
            if obj is not None:
                is_readonly = not obj.is_editable_by(request.user)
                if is_readonly:
                    extra_context["adminform_class"] = "is-readonly-form"
        else:
            work_pattern = WorkPattern.get_work_pattern(request.user.member)

        # 就業パターンの情報を取得して、テンプレートに渡す
        if work_pattern is not None:
            extra_context["work_duration"] = f"{work_pattern.start_time.strftime('%H:%M')} - {work_pattern.end_time.strftime('%H:%M')}"
            for i, duration in enumerate(work_pattern.get_break_durations()):
                if duration[0] and duration[1]:
                    name = f"break{i}_duration" if i > 0 else "lunch_break_duration"
                    extra_context[name] = f"{duration[0].strftime('%H:%M')} - {duration[1].strftime('%H:%M')}"

        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def save_formset(self, request, form, formset, change):
        # 1. Save the inline formset instances first
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()

        # Handle deleted inline objects
        for obj in formset.deleted_objects:
            obj.delete()

        # 2. Sum model instance methods for DailyAttendance
        if formset.model == DailyAttendance:
            parent_instance = form.instance  # MonthlyAttendance instance

            # Fetch fresh inline records from DB (or evaluate in-memory saved instances)
            daily_records = parent_instance.daily_attendances.all()

            # Sum the return value of actual_work_minutes() for each record
            parent_instance.actual_work_minutes = sum(record.actual_work_minutes or 0 for record in daily_records)
            parent_instance.overtime_minutes = sum(record.overtime_minutes or 0 for record in daily_records)
            parent_instance.night_work_minutes = sum(record.night_work_minutes or 0 for record in daily_records)
            parent_instance.worked_days = sum(1 if record.is_present() else 0 for record in daily_records)
            parent_instance.paid_leave_days = sum(record.get_paid_leave_days() or 0 for record in daily_records)
            parent_instance.standard_working_days = sum(1 if record.is_work_day() else 0 for record in daily_records)
            parent_instance.absence_days = sum(1 if record.date_status == DailyAttendance.DateStatus.ABSENCE else 0 for record in daily_records)
            parent_instance.early_leave_days = sum(1 if (record.early_leave_minutes or 0) > 0 else 0 for record in daily_records)
            parent_instance.late_days = sum(1 if (record.late_minutes or 0) > 0 else 0 for record in daily_records)
            parent_instance.total_absence_minutes = sum(
                (record.early_leave_minutes or 0)
                + (record.late_minutes or 0)
                + (record.work_pattern.get_standard_work_minutes() if record.date_status == DailyAttendance.DateStatus.ABSENCE else 0)
                for record in daily_records
            )

            # 3. Update the parent instance
            parent_instance.save(
                update_fields=[
                    "actual_work_minutes",
                    "overtime_minutes",
                    "night_work_minutes",
                    "worked_days",
                    "paid_leave_days",
                    "standard_working_days",
                    "absence_days",
                    "early_leave_days",
                    "late_days",
                    "total_absence_minutes",
                ]
            )
