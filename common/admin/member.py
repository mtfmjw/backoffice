from django.contrib import admin
from django.contrib.admin import display

from backoffice.admin import admin_site
from common.models import Member

from .base import BaseModelAdmin


@admin.register(Member, site=admin_site)
class MemberAdmin(BaseModelAdmin):
    has_add_permission = lambda self, request: False
    readonly_fields = ("user",) + BaseModelAdmin.readonly_fields
    list_display = ("full_name", "user", "email", "organization") + BaseModelAdmin.list_display
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "organization__code",
        "organization__name",
    )
    list_select_related = ("user", "organization")
    list_filter = ("organization",) + BaseModelAdmin.list_filter
    fieldsets = (
        (
            None,
            {
                "fields": (("user", "email"), ("organization", "manager_flag"), "work_pattern"),
            },
        ),
    )

    @display(description="Full Name")
    def full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}"
