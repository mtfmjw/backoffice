from django.conf import settings
from django.contrib import admin
from django.contrib.admin import display
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import CSV
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.form import DirectExportForm
from common.models import Member, Organization, WorkPattern

from .base import BaseModelAdminMixin


class MemberResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Member
        import_id_fields = ("email",)
        fields = (
            "user__username",
            "email",
            "organization__code",
            "work_pattern__name",
            "manage_flag",
            "valid_flag",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )
        export_order = (
            "user__username",
            "email",
            "organization__code",
            "work_pattern__name",
            "manage_flag",
            "valid_flag",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )

    User = fields.Field(
        attribute="user",
        column_name="user_username",
        widget=ForeignKeyWidget(settings.AUTH_USER_MODEL, field="username"),
    )

    Organization = fields.Field(
        attribute="organization",
        column_name="organization_code",
        widget=ForeignKeyWidget(Organization, field="code"),
    )

    WorkPattern = fields.Field(
        attribute="work_pattern",
        column_name="work_pattern_name",
        widget=ForeignKeyWidget(WorkPattern, field="name"),
    )


@admin.register(Member, site=admin_site)
class MemberAdmin(BaseModelAdminMixin, ImportExportModelAdmin):
    resource_class = MemberResource
    formats = (CSV,)
    export_form_class = DirectExportForm

    has_add_permission = lambda self, request: False
    readonly_fields = ("user",) + BaseModelAdminMixin.readonly_fields
    list_display = ("full_name", "user", "email", "organization") + BaseModelAdminMixin.list_display
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "organization__code",
        "organization__name",
    )
    list_select_related = ("user", "organization")
    list_filter = ("organization",) + BaseModelAdminMixin.list_filter
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
