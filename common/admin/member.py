from django.contrib import admin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.admin.filters import SimpleOrganizationFilter
from common.models import Member, Organization, WorkPattern

from .base import ImportBaseModelResourceMixin, RowScopedBaseModelAdmin

User = get_user_model()


class MemberResource(ImportBaseModelResourceMixin, resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Member
        import_id_fields = ("email",)
        fields = (
            "user",
            "email",
            "organization",
            "organization__name",
            "work_pattern",
            "work_pattern__name",
            "valid_flag",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )

    user = fields.Field(
        attribute="user",
        column_name="user_username",
        widget=ForeignKeyWidget(User, field="username"),
    )

    organization = fields.Field(
        attribute="organization",
        column_name="organization_code",
        widget=ForeignKeyWidget(Organization, field="code"),
    )

    work_pattern = fields.Field(
        attribute="work_pattern",
        column_name="work_pattern_no",
        widget=ForeignKeyWidget(WorkPattern, field="no"),
    )


@admin.register(Member, site=admin_site)
class MemberAdmin(RowScopedBaseModelAdmin):
    resource_class = MemberResource

    readonly_fields = ("user", "is_organization_manager")
    list_display = ("full_name", "user", "email", "organization", "is_organization_manager", "work_pattern")
    list_filter = (SimpleOrganizationFilter,)
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "organization__code",
        "organization__name",
    )
    list_select_related = ("user", "organization")
    fields = (("user", "email"), ("organization", "is_organization_manager"), ("work_pattern",))

    @display(description=_("Full Name"))
    def full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}"

    @display(description=_("Is Organization Manager"), boolean=True)
    def is_organization_manager(self, obj) -> bool:
        if obj is None:
            return False
        return obj.is_organization_manager() or obj.is_company_executive()

    def has_add_permission(self, request):
        """Members cannot be added via the admin interface. They are created automatically when a user is created."""
        return False

    def has_import_permission(self, request):
        return self.has_change_permission(request)


# print Method Resolution Order of MemberAdmin class
# print([cls.__name__ for cls in MemberAdmin.__mro__])
# Find which class in the MRO actually owns the active has_add_permission implementation
# print(MemberAdmin.has_add_permission.__qualname__)
