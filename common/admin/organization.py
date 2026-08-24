from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import CSV
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.admin.filters import SimpleOrganizationFilter
from common.form import DirectExportForm
from common.models import Organization, WorkPattern

from .base import BaseModelAdminMixin


class OrganizationResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Organization
        import_id_fields = ("code",)
        fields = ("code", "name", "parent", "work_pattern", "valid_flag", "created_at", "created_by", "updated_at", "updated_by")
        export_order = ("code", "name", "parent", "work_pattern", "valid_flag", "created_at", "created_by", "updated_at", "updated_by")

    parent = fields.Field(
        attribute="parent",
        column_name="parent_code",
        widget=ForeignKeyWidget(Organization, field="code"),
    )

    work_pattern = fields.Field(
        attribute="work_pattern",
        column_name="work_pattern_name",
        widget=ForeignKeyWidget(WorkPattern, field="name"),
    )


@admin.register(Organization, site=admin_site)
class OrganizationAdmin(BaseModelAdminMixin, ImportExportModelAdmin):
    resource_class = OrganizationResource
    formats = (CSV,)
    export_form_class = DirectExportForm

    list_display = ("code", "name", "parent", "work_pattern") + BaseModelAdminMixin.list_display
    list_filter = (SimpleOrganizationFilter,) + BaseModelAdminMixin.list_filter
    search_fields = ("code", "name")
    list_select_related = ("parent",)
    fieldsets = (
        (
            None,
            {
                "fields": (("code", "name", "parent"), "work_pattern"),
            },
        ),
    )
