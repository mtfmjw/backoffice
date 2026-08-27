import datetime

from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter, display
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Q
from django.forms import TextInput
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from backoffice.admin import admin_site
from common.admin.base import BaseModelAdminMixin, MemberScopedModelAdminMixin
from common.models import WorkPattern
from common.utils import minutes2str
from kintai.models import ApproveStatus, DailyAttendance, MonthlyAttendance

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
class MonthlyAttendanceAdmin(MemberScopedModelAdminMixin, admin.ModelAdmin):
    change_list_template = "kintai/monthlyattendance/change_list.html"
    change_form_template = "kintai/monthlyattendance/change_form.html"
    form = MonthlyAttendanceForm
    save_on_top = True
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
        # self.model.is_editable_by()によりCSSで編集可不可を制御するため、常にTrueを返す
        return self.model.is_authorized(request.user)

    def is_all_organizations_accessible(self, request):
        return super().is_all_organizations_accessible(request) or (
            getattr(request.user, "member", None) is not None and request.user.member.is_attendance_management_staff()
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # If your default filter kicks in when parameter is empty, fall back to default
        month_filtered = request.GET.get("month", localdate().strftime("%Y-%m"))

        # used internally to redirect users back to the filtered list view after saving an object
        extra_context["preserved_filters"] = self.get_preserved_filters(request)

        # Inject custom query string for the Add URL
        extra_context["month_filtered"] = month_filtered

        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        # 未申請のものは本人のみ表示、申請済み以降のものは本人以外も表示
        queryset = queryset.filter(Q(member=request.user.member) | ~Q(approve_status=ApproveStatus.DRAFT))

        return queryset

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

            extra_context["show_save_and_add_another"] = False
            obj = self.get_object(request, object_id)
            if obj.is_editable_by(request.user):
                extra_context["show_apply_button"] = True
                extra_context["show_save"] = True
                extra_context["show_save_and_continue"] = True
                extra_context["show_reject_button"] = False
                extra_context["next"] = False
                extra_context["apply_button_name"] = "_apply"
                extra_context["apply_button_label"] = _("Apply")
            else:
                extra_context["adminform_class"] = "is-readonly-form"

                extra_context["show_save"] = False
                extra_context["show_save_and_continue"] = False
                extra_context["next"] = True
                if obj.approve_status in [ApproveStatus.REJECTED, ApproveStatus.FINALIZED]:
                    extra_context["show_apply_button"] = False
                    extra_context["show_reject_button"] = False
                else:
                    login_user = request.user
                    if obj.approve_status == ApproveStatus.APPLIED:
                        extra_context["show_apply_button"] = obj.is_approvable_by(login_user)
                        extra_context["show_reject_button"] = obj.is_approvable_by(login_user)
                        extra_context["apply_button_name"] = "_approve"
                        extra_context["apply_button_label"] = _("Approve")
                        extra_context["save_and_add_label"] = _("Approve and Go to Next")
                    elif obj.approve_status == ApproveStatus.APPROVED:
                        extra_context["show_apply_button"] = obj.is_finalizable_by(login_user)
                        extra_context["show_reject_button"] = obj.is_finalizable_by(login_user)
                        extra_context["show_reject_button"] = True
                        extra_context["apply_button_name"] = "_finalize"
                        extra_context["apply_button_label"] = _("Finalize")
                        extra_context["save_and_add_label"] = _("Finalize and Go to Next")
        else:
            work_pattern = WorkPattern.get_work_pattern(request.user.member)
            extra_context["show_apply_button"] = True
            extra_context["apply_button_name"] = "_apply"
            extra_context["apply_button_label"] = _("Apply")

        # 就業パターンの情報を取得して、テンプレートに渡す
        if work_pattern is not None:
            extra_context["work_duration"] = f"{work_pattern.start_time.strftime('%H:%M')} - {work_pattern.end_time.strftime('%H:%M')}"
            for i, duration in enumerate(work_pattern.get_break_durations()):
                if duration[0] and duration[1]:
                    name = f"break{i}_duration" if i > 0 else "lunch_break_duration"
                    extra_context[name] = f"{duration[0].strftime('%H:%M')} - {duration[1].strftime('%H:%M')}"

        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if "_apply" in request.POST:
            obj.approve_status = ApproveStatus.APPLIED
        elif "_approve" in request.POST:
            obj.approve_status = ApproveStatus.APPROVED
        elif "_finalize" in request.POST:
            obj.approve_status = ApproveStatus.FINALIZED
        elif "_reject" in request.POST:
            obj.approve_status = ApproveStatus.REJECTED
        elif "_reapply" in request.POST:
            obj.approve_status = ApproveStatus.APPLIED

        super().save_model(request, obj, form, change)

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
