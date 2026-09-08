from datetime import datetime
from functools import partial
from urllib.parse import quote, urlencode

import openpyxl
from django import forms
from django.contrib import admin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Q
from django.forms import TextInput
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.admin.base import ApprovedBaseModelAdmin, ImportBaseModelResourceMixin
from common.const import ApproveStatus
from common.models import WorkPattern
from common.models.member import Member
from common.utils import minutes2str
from kintai.ldjp.attendance import get_attendance_sheet_file_name, write_attendance_sheet
from kintai.ldjp.const import ATTENDANCE_SHEET, DOWNLOAD_FOLDER
from kintai.models import MonthlyAttendance

from .common import MonthFilter
from .daily_attendance import DailyAttendanceInline

User = get_user_model()


class MonthlyAttendanceForm(forms.ModelForm):
    approve_note = forms.CharField(
        label=_("Approve Note"),
        widget=TextInput(
            attrs={
                "placeholder": _(
                    "終了時刻に開始時刻より早い時間を入力した場合、終了時刻は翌日の時刻として扱われます。却下時は、理由をここに記入してください。"
                )
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
            "work_pattern",
            "member__work_pattern__name",
            "approve_status",
            "worked_days",
            "standard_working_days",
            "working_time",
            "overtime",
            "night_working_time",
            "taken_paid_leaves",
            "absence_days",
            "early_leave_days",
            "late_days",
            "approve_note",
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


def call_calculate_working_time(member_id, month, username):
    with connection.cursor() as cursor:
        cursor.execute("CALL calculate_working_time(%s, %s, %s);", [member_id, month, username])


@admin.register(MonthlyAttendance, site=admin_site)
class MonthlyAttendanceAdmin(ApprovedBaseModelAdmin):
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
        "display_taken_paid_leaves",
        "display_paid_leave_available",
        "display_overtime_125",
        "display_overtime_150",
        "display_off_day_125",
        "display_off_day_150",
        "display_holiday_135",
        "display_holiday_160",
        "display_night_time_025",
        "display_absence_days",
        "display_early_leave_days",
        "display_late_days",
    )
    search_fields = ("member__user__username", "member__user__last_name", "member__user__first_name", "member__organization__name")
    list_select_related = ("member", "work_pattern")
    list_filter = (MonthFilter,)
    fields = ("approve_note",)
    inlines = (DailyAttendanceInline,)

    @display(description=_("Month"))
    def display_month(self, obj) -> str:
        return obj.month.strftime("%Y/%m")

    @display(description=_("Days Worked"))
    def display_worked_days(self, obj) -> str:
        return f"{obj.worked_days:.1f}日" if obj is not None and obj.worked_days else "-"

    @display(description=_("Standard Working Days"))
    def display_standard_working_days(self, obj) -> str:
        return f"{obj.standard_working_days}日" if obj is not None and obj.standard_working_days else "-"

    @display(description=_("Actual Working Time"))
    def display_working_time(self, obj) -> str:
        return minutes2str(obj.actual_work_minutes) if obj is not None else "-"

    @display(description=_("Overtime 1.25"))
    def display_overtime_125(self, obj) -> str:
        return minutes2str(obj.overtime_125) if obj is not None else "-"

    @display(description=_("Overtime 1.50"))
    def display_overtime_150(self, obj) -> str:
        return minutes2str(obj.overtime_150) if obj is not None else "-"

    @display(description=_("Night Work 0.25"))
    def display_night_time_025(self, obj) -> str:
        return minutes2str(obj.night_time_025) if obj is not None else "-"

    @display(description=_("Off Day 1.25"))
    def display_off_day_125(self, obj) -> str:
        return minutes2str(obj.off_day_125) if obj is not None else "-"

    @display(description=_("Off Day 1.50"))
    def display_off_day_150(self, obj) -> str:
        return minutes2str(obj.off_day_150) if obj is not None else "-"

    @display(description=_("Holiday 1.35"))
    def display_holiday_135(self, obj) -> str:
        return minutes2str(obj.holiday_135) if obj is not None else "-"

    @display(description=_("Holiday 1.60"))
    def display_holiday_160(self, obj) -> str:
        return minutes2str(obj.holiday_160) if obj is not None else "-"

    @display(description=_("Paid Leave Days"))
    def display_taken_paid_leaves(self, obj) -> str:
        return f"{obj.taken_paid_leaves:.1f}日" if obj is not None and obj.taken_paid_leaves else "-"

    @display(description=_("Paid Leave Available"))
    def display_paid_leave_available(self, obj) -> str:
        available = obj.member.paid_leaves.first().available_days if obj is not None and obj.member.paid_leaves.exists() else 0
        return f"{available:.1f}日" if available else "-"

    @display(description=_("Absence Days"))
    def display_absence_days(self, obj) -> str:
        return f"{obj.absence_days}日" if obj is not None and obj.absence_days else "-"

    @display(description=_("Early Leave Days"))
    def display_early_leave_days(self, obj) -> str:
        return f"{obj.early_leave_days}回" if obj is not None and obj.early_leave_days else "-"

    @display(description=_("Late Days"))
    def display_late_days(self, obj) -> str:
        return f"{obj.late_days}回" if obj is not None and obj.late_days else "-"

    def has_change_permission(self, request, obj=None):
        # self.model.is_editable_by()によりCSSで編集可不可を制御するため、常にTrueを返す
        return self.model.is_authorized(request.user)

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return False  # 月次勤怠は一覧画面から削除不可
        return super().has_delete_permission(request, obj)

    def has_import_permission(self, request):
        return False  # 月次勤怠はインポート不可

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
                cursor.execute("""CALL calculate_working_time(%s, %s, %s);""", [member.id, first_day, request.user.username])

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
        extra_context["overtime_125_label"] = _("Overtime 1.25")
        extra_context["overtime_150_label"] = _("Overtime 1.50")
        extra_context["off_day_125_label"] = _("Off Day 1.25")
        extra_context["off_day_150_label"] = _("Off Day 1.50")
        extra_context["holiday_135_label"] = _("Holiday 1.35")
        extra_context["holiday_160_label"] = _("Holiday 1.60")
        extra_context["night_time_025_label"] = _("Night Work 0.25")
        extra_context["taken_paid_leaves_label"] = _("Paid Leave Days")
        extra_context["paid_leave_available_label"] = _("Paid Leave Available")
        extra_context["absence_days_label"] = _("Absence Days")
        extra_context["early_leave_days_label"] = _("Early Leave Days")
        extra_context["late_days_label"] = _("Late Days")

        if object_id is not None:
            obj = self.get_object(request, object_id)
            extra_context["worked_days"] = self.display_worked_days(obj)
            extra_context["standard_working_days"] = self.display_standard_working_days(obj)
            extra_context["actual_working_time"] = self.display_working_time(obj)
            extra_context["overtime_125"] = self.display_overtime_125(obj)
            extra_context["overtime_150"] = self.display_overtime_150(obj)
            extra_context["off_day_125"] = self.display_off_day_125(obj)
            extra_context["off_day_150"] = self.display_off_day_150(obj)
            extra_context["holiday_135"] = self.display_holiday_135(obj)
            extra_context["holiday_160"] = self.display_holiday_160(obj)
            extra_context["night_time_025"] = self.display_night_time_025(obj)
            extra_context["taken_paid_leaves"] = self.display_taken_paid_leaves(obj)
            extra_context["paid_leave_available"] = self.display_paid_leave_available(obj)
            extra_context["absence_days"] = self.display_absence_days(obj)
            extra_context["early_leave_days"] = self.display_early_leave_days(obj)
            extra_context["late_days"] = self.display_late_days(obj)
            work_pattern = obj.work_pattern if obj is not None else None

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

    def get_inline_instances(self, request, obj=None):
        # Hide inlines on submit so Django skips validation & saving completely
        if request.method == "POST" and ("_approve" in request.POST or "_confirm" in request.POST or "_reject" in request.POST):
            return []
        return super().get_inline_instances(request, obj)

    def save_related(self, request, form, formsets, change):
        if request.method == "POST" and ("_approve" in request.POST or "_reject" in request.POST):
            # skip saving related objects
            return
        elif request.method == "POST" and "_confirm" in request.POST:
            instance = form.instance

            if instance.taken_paid_leaves and instance.member.paid_leave_available >= instance.taken_paid_leaves:
                instance.member.paid_leave_available = instance.member.paid_leave_available - instance.taken_paid_leaves
                instance.member.save()
            return

        super().save_related(request, form, formsets, change)

        # Get the saved parent instance
        monthly_attendance = form.instance

        # Schedule the procedure to execute AFTER the current database transaction commits
        member_id = monthly_attendance.member.id
        month = monthly_attendance.month

        # Register it to run AFTER the transaction commits
        transaction.on_commit(partial(call_calculate_working_time, member_id, month, request.user.username))

    def has_confirm_permission(self, request):
        """Check if the user has permission to confirm the object."""
        return request.user.member.is_accounting_staff or super().has_confirm_permission(request)

    def has_reject_permission(self, request):
        """Check if the user has permission to reject the object."""
        return request.user.member.is_accounting_staff or super().has_reject_permission(request)

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
