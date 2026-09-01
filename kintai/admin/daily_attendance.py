# admin.py
from datetime import timedelta

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime, AdminTimeWidget
from django.db import models
from django.forms.models import BaseInlineFormSet
from django.forms.widgets import TextInput
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.models.work_pattern import WorkPattern
from common.utils import convert2datetime, convert2duration, convert2localtime
from common.validation import mandatory_validation
from kintai.const import DateStatus, DateType
from kintai.models import DailyAttendance


class DailyAttendanceInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fetch choices ONCE for all forms in the formset
        work_pattern_choices = [(wp.pk, str(wp)) for wp in WorkPattern.get_all_work_patterns().values()]
        for form in self.forms:
            form.fields["work_pattern"].choices = work_pattern_choices


class DailyAttendanceInlineForm(forms.ModelForm):
    clock_in_time_only = forms.TimeField(
        label=_("Clock In"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), input_formats=["%H:%M"], required=False
    )
    clock_out_time_only = forms.TimeField(
        label=_("Clock Out"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), input_formats=["%H:%M"], required=False
    )
    absence_start = forms.TimeField(label=_("Absence Start"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), required=False)
    absence_end = forms.TimeField(label=_("Absence End"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), required=False)
    note = forms.CharField(
        label=_("Note"),
        widget=TextInput(attrs={"placeholder": _("休憩については実際休んだ分だけチェックしてください。")}),
        required=False,
    )

    class Meta:
        model = DailyAttendance
        fields = "__all__"
        widgets = {"date_type": forms.HiddenInput()}  # noqa: RUF012

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            if self.instance.clock_in_time:
                local_in = convert2localtime(self.instance.clock_in_time)
                self.initial["clock_in_time_only"] = local_in.strftime("%H:%M")

            if self.instance.clock_out_time:
                local_out = convert2localtime(self.instance.clock_out_time)
                self.initial["clock_out_time_only"] = local_out.strftime("%H:%M")

    def clean(self):
        cleaned_data = super().clean()

        date_status = cleaned_data.get("date_status")
        if date_status in (
            DateStatus.PRESENT,
            DateStatus.MORNING_PAID_LEAVE,
            DateStatus.AFTERNOON_PAID_LEAVE,
        ):
            mandatory_validation(self, cleaned_data, "work_pattern", _("Work Pattern"))
            mandatory_validation(self, cleaned_data, "clock_in_time_only", _("Clock In"))
            mandatory_validation(self, cleaned_data, "clock_out_time_only", _("Clock Out"))

        date_type = cleaned_data.get("date_type")
        # 休日の場合、日次ステータスは空白にするか、「出勤」のみ許可する
        if date_type != DateType.WORK_DAY and date_status is not None and date_status != DateStatus.PRESENT:
            self.add_error("date_status", _("Date Status cannot be set to anything other than Present on a Holiday."))

        clock_in_time = cleaned_data.get("clock_in_time_only")
        clock_out_time = cleaned_data.get("clock_out_time_only")
        work_pattern = cleaned_data.get("work_pattern")
        if clock_in_time and clock_out_time and work_pattern:
            __, work_end = convert2duration(timezone.localdate(), clock_in_time, clock_out_time)
            next_day_start = convert2datetime(timezone.localdate() + timedelta(days=1), work_pattern.start_time)
            if work_end > next_day_start:
                self.add_error("clock_out_time_only", _("Clock-out time must be before the next day's start time."))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        clock_in_time, clock_out_time = convert2duration(
            instance.day, self.cleaned_data.get("clock_in_time_only"), self.cleaned_data.get("clock_out_time_only")
        )

        instance.clock_in_time = clock_in_time
        instance.clock_out_time = clock_out_time

        if commit:
            instance.save()
        return instance


class DailyAttendanceInline(admin.TabularInline):
    model = DailyAttendance
    form = DailyAttendanceInlineForm
    formset = DailyAttendanceInlineFormSet
    extra = 0
    can_delete = False
    fields = (
        "date_status",
        "work_pattern",
        "clock_in_time_only",
        "clock_out_time_only",
        "has_lunch_break",
        "has_break1",
        "has_break2",
        "has_break3",
        "has_break4",
        "has_break5",
        "absence_start",
        "absence_end",
        "note",
        "date_type",
    )

    formfield_overrides = {models.DateTimeField: {"widget": AdminSplitDateTime}}  # noqa: RUF012

    class Media:
        css = {"all": ("common/css/disable_time_related_icons.css",)}  # noqa: RUF012

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Fetch foreign keys in 1 query instead of N queries
        return qs.select_related("work_pattern")
