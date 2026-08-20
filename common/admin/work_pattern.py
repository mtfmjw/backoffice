from django.contrib import admin
from django.contrib.admin import display
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import CSV
from import_export.instance_loaders import CachedInstanceLoader

from backoffice.admin import admin_site
from common.models import WorkPattern
from common.utils import duration2str

from .base import CommonAdminMixin, MasterImportExportPermissionMixin


class WorkPatternResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        instance_loader_class = CachedInstanceLoader

        model = WorkPattern
        fields = (
            "name",
            "start_time",
            "end_time",
            "standard_work_time",
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
        )
        import_id_fields = ("name",)


@admin.register(WorkPattern, site=admin_site)
class WorkPatternAdmin(CommonAdminMixin, MasterImportExportPermissionMixin, ImportExportModelAdmin):
    resource_class = WorkPatternResource
    formats = (CSV,)
    list_display = (
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
    search_fields = ("name",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    ("start_time", "end_time", "standard_work_time"),
                    ("lunch_break_start_time", "lunch_break_end_time", "half_day_time"),
                    ("break1_start_time", "break1_end_time"),
                    ("break2_start_time", "break2_end_time"),
                    ("break3_start_time", "break3_end_time"),
                    ("break4_start_time", "break4_end_time"),
                    ("break5_start_time", "break5_end_time"),
                ),
            },
        ),
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
