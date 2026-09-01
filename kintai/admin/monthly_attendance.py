from datetime import datetime
from urllib.parse import quote, urlencode

import openpyxl
from dateutil.relativedelta import relativedelta
from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter, display
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Q
from django.forms import TextInput
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.timezone import localdate, localtime
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.admin.base import ImportBaseModelResourceMixin, RowScopedBaseModelAdmin
from common.models import WorkPattern
from common.models.member import Member, get_user_full_name
from common.utils import convert2str, minutes2str
from kintai.const import ApproveStatus
from kintai.ldjp.attendance import get_attendance_sheet_file_name, write_attendance_sheet
from kintai.ldjp.const import ATTENDANCE_SHEET, DOWNLOAD_FOLDER
from kintai.models import MonthlyAttendance

from .daily_attendance import DailyAttendanceInline

User = get_user_model()


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


class MonthlyAttendanceResource(ImportBaseModelResourceMixin, resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = MonthlyAttendance
        import_id_fields = ("member", "month")
        fields = (
            "month",
            "member__user__username",
            "member__user__last_name",
            "member__user__first_name",
            "member__email",
            "member__organization__code",
            "member__organization__name",
            "member__work_pattern__no",
            "member__work_pattern__name",
            "approve_status",
            "worked_days",
            "standard_working_days",
            "working_time",
            "overtime",
            "night_working_time",
            "paid_leave_days",
            "absence_days",
            "early_leave_days",
            "late_days",
            "total_absence_minutes",
            "note",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "applied_by",
            "applied_at",
            "approved_by",
            "approved_at",
            "confirmed_by",
            "confirmed_at",
        )

    member = fields.Field(
        attribute="member",
        column_name="member__email",
        widget=ForeignKeyWidget(Member, field="email"),
    )

    work_pattern = fields.Field(
        attribute="work_pattern",
        column_name="work_pattern_no",
        widget=ForeignKeyWidget(WorkPattern, field="no"),
    )


@admin.register(MonthlyAttendance, site=admin_site)
class MonthlyAttendanceAdmin(RowScopedBaseModelAdmin):
    change_list_template = "kintai/monthlyattendance/change_list.html"
    change_form_template = "kintai/monthlyattendance/change_form.html"
    form = MonthlyAttendanceForm
    save_on_top = False
    resource_class = MonthlyAttendanceResource
    list_display = (
        "member",
        "display_month",
        "belong",
        "approve_status",
        "display_worked_days",
        "display_standard_working_days",
        "display_working_time",
        "display_paid_leave_days",
        "absence_days",
        "early_leave_days",
        "late_days",
        "display_total_absence_minutes",
    )
    search_fields = ("member__user__username", "member__user__last_name", "member__user__first_name", "member__organization__name")
    list_select_related = ("member", "work_pattern")
    list_filter = (MonthFilter, "approve_status")
    fields = ("note",)
    readonly_fields = (
        "display_worked_days",
        "display_standard_working_days",
        "display_working_time",
        "display_paid_leave_days",
        "absence_days",
        "early_leave_days",
        "late_days",
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
        return f"{obj.worked_days:.1f}日"

    @display(description=_("Standard Working Days"))
    def display_standard_working_days(self, obj) -> str:
        return f"{obj.standard_working_days}日"

    @display(description=_("Actual Working Time"))
    def display_working_time(self, obj) -> str:
        return minutes2str(obj.actual_work_minutes)

    @display(description=_("Paid Leave Days"))
    def display_paid_leave_days(self, obj) -> str:
        return f"{obj.paid_leave_days:.1f}日" if obj.paid_leave_days is not None else ""

    @display(description=_("Total Absence Time"))
    def display_total_absence_minutes(self, obj) -> str:
        return minutes2str(obj.total_absence_minutes)

    @display(description=_("Audit Info"))
    def audit_info(self, obj):
        """Display audit information for the object, including created_by, created_at, updated_by, and updated_at."""

        if obj is None:
            return ""

        if obj.applied_at is None:
            return super().audit_info(obj)

        # 申請者情報
        applied_by = get_user_full_name(obj.applied_by) or "-"
        applied_at = convert2str(obj.applied_at)
        audit_info = f"{_('Applied by')}：{applied_by}　{_('Applied at')}：{applied_at}　"
        # 承認者情報
        approved_by = get_user_full_name(obj.approved_by) or "-"
        approved_at = convert2str(obj.approved_at)
        audit_info += f"　{_('Approved by')}：{approved_by}　{_('Approved at')}：{approved_at}　"
        # 確定者情報
        confirmed_by = get_user_full_name(obj.confirmed_by) or "-"
        confirmed_at = convert2str(obj.confirmed_at)
        audit_info += f"　{_('Confirmed by')}：{confirmed_by}　{_('Confirmed at')}：{confirmed_at}"
        return audit_info

    def has_add_permission(self, request):
        return request.user.is_authenticated and hasattr(request.user, "member")

    def has_change_permission(self, request, obj=None):
        # self.model.is_editable_by()によりCSSで編集可不可を制御するため、常にTrueを返す
        return self.model.is_authorized(request.user)

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False  # 月次勤怠は一覧画面から削除不可
        return super().has_delete_permission(request, obj)

    def has_import_permission(self, request):
        return True  # 月次勤怠はインポート不可

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

    def add_view(self, request, form_url="", extra_context=None):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        member = request.user.member
        month_str = request.GET.get("month", localdate().strftime("%Y-%m"))
        first_day = datetime.strptime(month_str, "%Y-%m").date()  # noqa: DTZ007
        attendance = MonthlyAttendance.objects.filter(member=member, month=first_day).first()
        if attendance is not None and attendance.valid_flag:
            attendance_id = attendance.id
        else:
            if attendance is not None and not attendance.valid_flag:
                attendance.delete()
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute("""CALL create_monthly_attendance(%s, %s, %s, %s);""", [member.id, first_day, request.user.username, 0])
                attendance_id = cursor.fetchone()[0]
                monthly_attendance = MonthlyAttendance.objects.get(id=attendance_id)
                for daily_attendance in monthly_attendance.daily_attendances.all():
                    daily_attendance.update_derived_fields()  # DailyAttendance instance
                    daily_attendance.save()
                monthly_attendance.update_derived_fields()  # MonthlyAttendance instance

        # 1. Get the current request's GET query string (e.g., "status=1&month=2026-08")
        # Or get it from request.META.get('HTTP_REFERER') if coming from a different view
        preserved_filters = request.GET.urlencode()

        # 2. Reverse the change form URL
        base_url = reverse("admin:kintai_monthlyattendance_change", args=(attendance_id,))

        # 3. Append _changelist_filters if filter parameters exist
        if preserved_filters:
            redirect_url = f"{base_url}?{urlencode({'_changelist_filters': preserved_filters})}"
        else:
            redirect_url = base_url

        return redirect(redirect_url)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        extra_context["worked_days_label"] = _("Days Worked")
        extra_context["standard_working_days_label"] = _("Standard Working Days")
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
            extra_context["standard_working_days"] = self.display_standard_working_days(obj)
            extra_context["actual_working_time"] = self.display_working_time(obj)
            extra_context["overtime"] = 0
            extra_context["night_working_time"] = 0
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
                if obj.approve_status in [ApproveStatus.REJECTED, ApproveStatus.CONFIRMED]:
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
                        extra_context["show_apply_button"] = obj.is_confirmable_by(login_user)
                        extra_context["show_reject_button"] = obj.is_confirmable_by(login_user)
                        extra_context["show_reject_button"] = True
                        extra_context["apply_button_name"] = "_confirm"
                        extra_context["apply_button_label"] = _("Confirm")
                        extra_context["save_and_add_label"] = _("Confirm and Go to Next")
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
            obj.applied_by = request.user.username
            obj.applied_at = localtime()
        elif "_approve" in request.POST:
            obj.approve_status = ApproveStatus.APPROVED
            obj.approved_by = request.user.username
            obj.approved_at = localtime()
        elif "_confirm" in request.POST:
            obj.approve_status = ApproveStatus.CONFIRMED
            obj.confirmed_by = request.user.username
            obj.confirmed_at = localtime()
        elif "_reject" in request.POST:
            obj.approve_status = ApproveStatus.REJECTED
        elif "_reapply" in request.POST:
            obj.approve_status = ApproveStatus.APPLIED
            obj.applied_by = request.user.username
            obj.applied_at = localtime()

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        # Save the inline formset instances first
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()

        # Handle deleted inline objects
        for obj in formset.deleted_objects:
            obj.delete()

        member = request.user.member
        month_str = request.GET.get("month", localdate().strftime("%Y-%m"))
        first_day = datetime.strptime(month_str, "%Y-%m").date()  # noqa: DTZ007
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("""CALL calculate_working_time(%s, %s, %s);""", [member.id, first_day, request.user.username])

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/export-attendance-sheet/",
                self.admin_site.admin_view(self.export_attendance_sheet),
                name="export-attendance-sheet",
            ),
        ]
        return custom_urls + urls

    def export_attendance_sheet(self, request, object_id):
        ma = get_object_or_404(MonthlyAttendance, pk=object_id)

        download_file_name = quote(get_attendance_sheet_file_name(ma.month, ma.member))
        template_path = DOWNLOAD_FOLDER / ATTENDANCE_SHEET
        wb = openpyxl.load_workbook(template_path)  # Set keep_vba=True if template is .xlsm
        ws = wb.active
        write_attendance_sheet(ws, self, ma)

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{download_file_name}"'

        wb.save(response)
        return response
