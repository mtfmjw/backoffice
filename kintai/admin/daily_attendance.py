# admin.py
from datetime import timedelta

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime, AdminTimeWidget
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.utils import convert2datetime, convert2duration
from common.validattion import mandattory_validation
from kintai.models import DailyAttendance


class DailyAttendanceInlineForm(forms.ModelForm):
    clock_in_time_only = forms.TimeField(
        label="出勤時刻", widget=AdminTimeWidget(format="%H:%M"), input_formats=["%H:%M", "%H:%M:%S"], required=False
    )
    clock_out_time_only = forms.TimeField(
        label="退勤時刻", widget=AdminTimeWidget(format="%H:%M"), input_formats=["%H:%M", "%H:%M:%S"], required=False
    )

    class Meta:
        model = DailyAttendance
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            if self.instance.clock_in_time:
                local_in = timezone.localtime(self.instance.clock_in_time)
                self.initial["clock_in_time_only"] = local_in.strftime("%H:%M")

            if self.instance.clock_out_time:
                local_out = timezone.localtime(self.instance.clock_out_time)
                self.initial["clock_out_time_only"] = local_out.strftime("%H:%M")

    def clean(self):
        cleaned_data = super().clean()

        date_status = cleaned_data.get("date_status")
        if date_status in (
            DailyAttendance.DateStatus.PRESENT,
            DailyAttendance.DateStatus.MORNING_PAID_LEAVE,
            DailyAttendance.DateStatus.AFTERNOON_PAID_LEAVE,
        ):
            mandattory_validation(self, cleaned_data, "work_pattern", _("Work Pattern"))
            mandattory_validation(self, cleaned_data, "clock_in_time_only", _("Clock In"))
            mandattory_validation(self, cleaned_data, "clock_out_time_only", _("Clock Out"))

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
        "other_break_minutes",
        "note",
    )

    formfield_overrides = {models.DateTimeField: {"widget": AdminSplitDateTime}}  # noqa: RUF012

    class Media:
        css = {"all": ("kintai/monthly_attendance_change_list.css",)}  # noqa: RUF012

    def has_add_permission(self, request, obj=None):
        return False
