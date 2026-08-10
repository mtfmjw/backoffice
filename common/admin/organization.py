from django.contrib import admin

from backoffice.admin import admin_site
from common.models import Organization

from .base import BaseModelAdmin


@admin.register(Organization, site=admin_site)
class OrganizationAdmin(BaseModelAdmin):
    list_display = ("code", "name", "parent") + BaseModelAdmin.list_display
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
