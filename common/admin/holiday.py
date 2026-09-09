from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.widgets import DateWidget

from backoffice.admin import admin_site
from common.models import Holiday

from .base import ImportBaseModelResourceMixin, MemberScopedBaseModelAdmin
from .filters import YearFilter


class HolidayResource(ImportBaseModelResourceMixin, resources.ModelResource):
    date = fields.Field(column_name="date", attribute="date", widget=DateWidget(format="%Y/%m/%d"))

    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        batch_size = 20000

        model = Holiday
        fields = ("date", "name", "type", "created_by", "created_at", "updated_by", "updated_at", "valid_flag")
        import_id_fields = ("date",)

    def before_import_row(self, row, **kwargs):
        """Set default type to NATIONAL_HOLIDAY if not provided in the import row."""
        if "type" not in row or not row["type"]:
            row["type"] = Holiday.Type.NATIONAL_HOLIDAY
        super().before_import_row(row, **kwargs)


@admin.register(Holiday, site=admin_site)
class HolidayAdmin(MemberScopedBaseModelAdmin):
    resource_class = HolidayResource

    list_display = ("date", "type", "name")
    list_filter = (YearFilter,)
    search_fields = ("type", "name")
    fields = (("date", "type"), "name")
