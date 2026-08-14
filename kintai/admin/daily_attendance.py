# admin.py
from django.contrib import admin
from django.contrib.admin.widgets import AdminTimeWidget
from django.db import models

from kintai.models.daily_attendance import DailyAttendance

# Choose one of the following:


class DailyAttendanceInline(admin.TabularInline):
    model = DailyAttendance
    extra = 0
    can_delete = False
    fields = (
        "date_status",
        "work_pattern",
        "clock_in_time",
        "clock_out_time",
        "has_lunch_break",
        "has_break1",
        "has_break2",
        "has_break3",
        "has_break4",
        "has_break5",
        "other_break_minutes",
        "note",
    )

    formfield_overrides = {models.DateTimeField: {"widget": AdminTimeWidget}}  # noqa: RUF012

    class Media:
        css = {"all": ("kintai/monthly_attendance_change_list.css",)}  # noqa: RUF012

    def has_add_permission(self, request, obj=None):
        return False
