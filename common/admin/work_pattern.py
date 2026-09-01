from django import forms
from django.contrib import admin
from django.contrib.admin import display
from django.utils.text import format_lazy
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.instance_loaders import CachedInstanceLoader

from backoffice.admin import admin_site
from common.models import WorkPattern
from common.utils import convert2duration, duration2minutes, duration2str
from common.validation import time_range_validation

from .base import ImportBaseModelResourceMixin, MemberScopedBaseModelAdmin


class WorkPatternResource(ImportBaseModelResourceMixin, resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        instance_loader_class = CachedInstanceLoader

        model = WorkPattern
        fields = (
            "no",
            "name",
            "start_time",
            "end_time",
            "standard_work_time",
            "half_day_time",
            "lunch_break_start_time",
            "lunch_break_end_time",
            "break1_start_time",
            "break1_end_time",
            "break2_start_time",
            "break2_end_time",
            "break3_start_time",
            "break3_end_time",
            "break4_start_time",
            "break4_end_time",
            "break5_start_time",
            "break5_end_time",
            "valid_flag",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
        )
        import_id_fields = ("no",)


class WorkPatternForm(forms.ModelForm):
    half_day_time = forms.TimeField(label=_("Half Day Time"), required=True, help_text="午前休の開始時刻、午後休の終了時刻")
    end_time = forms.TimeField(label=_("Standard End Time"), required=True, help_text="開始時刻より前になると翌日扱いになるので注意")

    class Meta:
        model = WorkPattern
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        time_range_validation(self, cleaned_data, "start_time", "end_time", _("Standard Start Time"), _("Standard End Time"))

        standard_work_time = cleaned_data.get("standard_work_time")
        if start_time is None and end_time is None and standard_work_time is None:
            self.add_error("start_time", _("Either start time and end time or standard work time must be provided."))
            self.add_error("end_time", _("Either start time and end time or standard work time must be provided."))
            self.add_error("standard_work_time", _("Either start time and end time or standard work time must be provided."))

        if start_time is not None and end_time is not None:
            standard_work_minutes = duration2minutes(convert2duration(localdate(), start_time, end_time))
            if standard_work_minutes > 6 * 60:  # 6時間超える勤務
                lunch_break_start_time = cleaned_data.get("lunch_break_start_time")
                lunch_break_end_time = cleaned_data.get("lunch_break_end_time")
                if lunch_break_start_time is None or lunch_break_end_time is None:
                    self.add_error(
                        "lunch_break_start_time", _("Lunch break start time and end time must be provided for work durations exceeding 6 hours.")
                    )
                    self.add_error(
                        "lunch_break_end_time", _("Lunch break start time and end time must be provided for work durations exceeding 6 hours.")
                    )
                else:
                    lunch_break_minutes = duration2minutes(convert2duration(localdate(), lunch_break_start_time, lunch_break_end_time))
                    if lunch_break_minutes < 45:  # 45分未満の昼休憩
                        self.add_error(
                            "lunch_break_start_time", _("Lunch break duration must be at least 45 minutes for work durations exceeding 6 hours.")
                        )
                        self.add_error(
                            "lunch_break_end_time", _("Lunch break duration must be at least 45 minutes for work durations exceeding 6 hours.")
                        )
                    elif standard_work_minutes > 8 * 60 and lunch_break_minutes < 60:  # 8時間超える勤務の60分未満の昼休憩
                        self.add_error(
                            "lunch_break_start_time", _("Lunch break duration must be at least 60 minutes for work durations exceeding 8 hours.")
                        )
                        self.add_error(
                            "lunch_break_end_time", _("Lunch break duration must be at least 60 minutes for work durations exceeding 8 hours.")
                        )

            time_range_validation(
                self, cleaned_data, "lunch_break_start_time", "lunch_break_end_time", _("Lunch Break Start Time"), _("Lunch Break End Time")
            )

        for i in range(1, 6):
            start_field_name = f"break{i}_start_time"
            end_field_name = f"break{i}_end_time"
            start_field_label = format_lazy("Break {i} Start Time", i=i)
            end_field_label = format_lazy("Break {i} End Time", i=i)
            time_range_validation(self, cleaned_data, start_field_name, end_field_name, start_field_label, end_field_label)

        return cleaned_data


@admin.register(WorkPattern, site=admin_site)
class WorkPatternAdmin(MemberScopedBaseModelAdmin):
    form = WorkPatternForm
    resource_class = WorkPatternResource
    list_display = (
        "no",
        "name",
        "working_duration",
        "standard_work_time",
        "half_day_time",
        "lunch_break_duration",
        "break1_duration",
        "break2_duration",
        "break3_duration",
        "break4_duration",
        "break5_duration",
    )
    list_display_links = ("name",)
    search_fields = ("name",)
    fields = (
        ("no", "name"),
        ("start_time", "end_time", "standard_work_time"),
        ("lunch_break_start_time", "lunch_break_end_time", "half_day_time"),
        ("break1_start_time", "break1_end_time"),
        ("break2_start_time", "break2_end_time"),
        ("break3_start_time", "break3_end_time"),
        ("break4_start_time", "break4_end_time"),
        ("break5_start_time", "break5_end_time"),
    )

    class Media:
        css = {"all": ("common/css/disable_time_related_icons.css",)}  # noqa: RUF012

    @display(description="勤務時間")
    def working_duration(self, obj):
        return duration2str((obj.start_time, obj.end_time))

    @display(description="昼休憩")
    def lunch_break_duration(self, obj):
        return duration2str((obj.lunch_break_start_time, obj.lunch_break_end_time))

    @display(description="休憩１")
    def break1_duration(self, obj):
        return duration2str((obj.break1_start_time, obj.break1_end_time))

    @display(description="休憩２")
    def break2_duration(self, obj):
        return duration2str((obj.break2_start_time, obj.break2_end_time))

    @display(description="休憩３")
    def break3_duration(self, obj):
        return duration2str((obj.break3_start_time, obj.break3_end_time))

    @display(description="休憩４")
    def break4_duration(self, obj):
        return duration2str((obj.break4_start_time, obj.break4_end_time))

    @display(description="休憩５")
    def break5_duration(self, obj):
        return duration2str((obj.break5_start_time, obj.break5_end_time))

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            # Editing an existing object
            readonly_fields.append("no")
        return readonly_fields
