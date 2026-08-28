from django.contrib import admin
from django.db.models import Case, When
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.admin.filters import SimpleOrganizationFilter
from common.models import Organization, WorkPattern

from .base import MemberScopedBaseModelAdmin


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
class OrganizationAdmin(MemberScopedBaseModelAdmin):
    resource_class = OrganizationResource

    list_display = ("code", "name", "parent", "work_pattern")
    list_filter = (SimpleOrganizationFilter,)
    search_fields = ("code", "name")
    list_select_related = ("parent",)
    fields = (("code", "name", "parent"), "work_pattern")

    def get_export_queryset(self, queryset=None):
        """Get the queryset for exporting data, ordering by the hierarchy of descendant organizations."""
        descendants = self.model.get_descendant_organizations()
        ordered_ids = [item[0] for item in descendants]
        if not ordered_ids:
            return Organization.objects.none()

        preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_ids)])
        return Organization.objects.filter(id__in=ordered_ids).order_by(preserved_order)
