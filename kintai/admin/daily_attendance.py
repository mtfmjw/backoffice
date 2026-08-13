# admin.py
from django.contrib import admin

from kintai.models.daily_attendance import DailyAttendance

# Choose one of the following:


class DailyAttendanceInline(admin.TabularInline):
    model = DailyAttendance
    extra = 0
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
