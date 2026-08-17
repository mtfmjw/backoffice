# admin.py
import datetime

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime, AdminTimeWidget
from django.db import models
from django.utils import timezone

from kintai.models.daily_attendance import DailyAttendance


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

    def save(self, commit=True):
        instance = super().save(commit=False)

        in_time_val = self.cleaned_data.get("clock_in_time_only")
        out_time_val = self.cleaned_data.get("clock_out_time_only")

        # Base date anchor (e.g. work_date or today's date)
        base_date = instance.day

        if in_time_val:
            in_dt = datetime.datetime.combine(base_date, in_time_val)
            instance.clock_in_time = timezone.make_aware(in_dt) if settings.USE_TZ else in_dt
        else:
            instance.clock_in_time = None

        if out_time_val:
            out_date = base_date

            # OVERNIGHT SHIFT DETECTOR:
            # If clock-out time (05:00) is less than or equal to clock-in time (09:00),
            # treat clock-out as the next calendar day (+1 day).
            if in_time_val and out_time_val <= in_time_val:
                out_date += datetime.timedelta(days=1)

            out_dt = datetime.datetime.combine(out_date, out_time_val)
            instance.clock_out_time = timezone.make_aware(out_dt) if settings.USE_TZ else out_dt
        else:
            instance.clock_out_time = None

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
