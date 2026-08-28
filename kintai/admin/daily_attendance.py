# admin.py
from datetime import timedelta

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminSplitDateTime, AdminTimeWidget
from django.db import models
from django.forms.widgets import TextInput
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.utils import convert2datetime, convert2duration, duration2minutes, get_overlap_minutes
from common.validation import mandatory_validation
from kintai.models import DailyAttendance
from kintai.models.daily_attendance import NIGHT_END_TIME, NIGHT_START_TIME


class DailyAttendanceInlineForm(forms.ModelForm):
    clock_in_time_only = forms.TimeField(
        label=_("Clock In"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), input_formats=["%H:%M"], required=False
    )
    clock_out_time_only = forms.TimeField(
        label=_("Clock Out"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), input_formats=["%H:%M"], required=False
    )
    day_absence = forms.TimeField(label=_("Day Absence"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), required=False)
    night_absence = forms.TimeField(label=_("Night Absence"), widget=AdminTimeWidget(format="%H:%M", attrs={"placeholder": "HH:MM"}), required=False)
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
            mandatory_validation(self, cleaned_data, "work_pattern", _("Work Pattern"))
            mandatory_validation(self, cleaned_data, "clock_in_time_only", _("Clock In"))
            mandatory_validation(self, cleaned_data, "clock_out_time_only", _("Clock Out"))

        date_type = cleaned_data.get("date_type")
        # 休日の場合、日次ステータスは空白にするか、「出勤」のみ許可する
        if date_type != DailyAttendance.DateType.WORK_DAY and date_status is not None and date_status != DailyAttendance.DateStatus.PRESENT:
            self.add_error("date_status", _("Date Status cannot be set to anything other than Present on a Holiday."))

        clock_in_time = cleaned_data.get("clock_in_time_only")
        clock_out_time = cleaned_data.get("clock_out_time_only")
        work_pattern = cleaned_data.get("work_pattern")
        if clock_in_time and clock_out_time and work_pattern:
            __, work_end = convert2duration(timezone.localdate(), clock_in_time, clock_out_time)
            next_day_start = convert2datetime(timezone.localdate() + timedelta(days=1), work_pattern.start_time)
            if work_end > next_day_start:
                self.add_error("clock_out_time_only", _("Clock-out time must be before the next day's start time."))

            day_absence = cleaned_data.get("day_absence")
            night_absence = cleaned_data.get("night_absence")
            if day_absence is not None:
                night_duration = convert2duration(timezone.localdate(), NIGHT_START_TIME, NIGHT_END_TIME)
                work_duration = convert2duration(timezone.localdate(), clock_in_time, clock_out_time)
                night_work_minutes = get_overlap_minutes(work_duration, night_duration)
                day_work_minutes = duration2minutes(work_duration) - night_work_minutes
                day_absence_minutes = day_absence.hour * 60 + day_absence.minute
                if day_absence_minutes >= day_work_minutes:
                    self.add_error("day_absence", _("Day Absence must be less than total work minutes."))
            if night_absence is not None:
                night_duration = convert2duration(timezone.localdate(), NIGHT_START_TIME, NIGHT_END_TIME)
                work_duration = convert2duration(timezone.localdate(), clock_in_time, clock_out_time)
                night_work_minutes = get_overlap_minutes(work_duration, night_duration)
                night_absence_minutes = night_absence.hour * 60 + night_absence.minute
                if night_absence_minutes >= night_work_minutes:
                    self.add_error("night_absence", _("Night Absence must be less than total night work minutes."))
        else:
            day_absence = cleaned_data.get("day_absence")
            night_absence = cleaned_data.get("night_absence")
            if day_absence is not None:
                self.add_error("day_absence", _("Day Absence cannot be set when clock-in and clock-out times are not provided."))
            if night_absence is not None:
                self.add_error("night_absence", _("Night Absence cannot be set when clock-in and clock-out times are not provided."))

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
        "day_absence",
        "night_absence",
        "note",
        "date_type",
    )

    formfield_overrides = {models.DateTimeField: {"widget": AdminSplitDateTime}}  # noqa: RUF012

    class Media:
        css = {"all": ("common/css/disable_time_related_icons.css",)}  # noqa: RUF012

    def has_add_permission(self, request, obj=None):
        return False
