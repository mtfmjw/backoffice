from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from backoffice.admin import admin_site
from common.models import Organization

from .base import BaseModelAdminMixin


@admin.register(Organization, site=admin_site)
class OrganizationAdmin(BaseModelAdminMixin, ImportExportModelAdmin):
    list_display = ("code", "name", "parent") + BaseModelAdminMixin.list_display
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
