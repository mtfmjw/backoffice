from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import DateWidget

from backoffice.admin import admin_site
from common.models import Holiday

from .filters import YearlyFilter


class HolidayResource(resources.ModelResource):
    date = fields.Field(column_name="date", attribute="date", widget=DateWidget(format="%Y/%m/%d"))

    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        batch_size = 20000

        model = Holiday
        fields = ("date", "name")
        import_id_fields = ("date",)

    def before_import_row(self, row, **kwargs):
        if "type" not in row or not row["type"]:
            row["type"] = Holiday.Type.NATIONAL_HOLIDAY
        super().before_import_row(row, **kwargs)


@admin.register(Holiday, site=admin_site)
class HolidayAdmin(ImportExportModelAdmin):
    resource_class = HolidayResource
    list_display = ("date", "type", "name")
    list_filter = (YearlyFilter,)
    search_fields = ("date", "name")
    fieldsets = (
        (
            None,
            {
                "fields": ("date", "type", "name"),
            },
        ),
    )
