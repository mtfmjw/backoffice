from django import forms
from django.contrib import admin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.admin.filters import SimpleOrganizationFilter
from common.models import Member, Organization, WorkPattern

from .base import ImportBaseModelResourceMixin, RowScopedBaseModelAdmin

User = get_user_model()


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        # Extract request passed from ModelAdmin
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if self.request and "_yearly_paid_leave" in self.request.POST:
            join_date = cleaned_data.get("join_date")
            if join_date is None:
                self.add_error("join_date", _("Join date is required to apply for yearly paid leave."))
            else:
                today = timezone.localdate()
                reference_date = today.replace(month=10, day=1)
                one_year_ago = reference_date.replace(year=reference_date.year - 1)
                # 直前の10月1日以後に入社した場合、計算有給休暇計算の対象とする
                if join_date < one_year_ago:
                    self.add_error("join_date", _("Join date must be within the past year to apply for yearly paid leave."))
        return cleaned_data


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
    form = MemberForm
    resource_class = MemberResource

    list_display = ("full_name", "user", "email", "organization", "is_organization_manager", "work_pattern", "join_date")
    list_filter = (SimpleOrganizationFilter,)
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "organization__code",
        "organization__name",
    )
    list_select_related = ("user", "organization")
    fields = (("user", "email"), ("organization", "is_organization_manager"), ("join_date", "work_pattern"))

    @display(description=_("Full Name"))
    def full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}"

    @display(description=_("Is Organization Manager"), boolean=True)
    def is_organization_manager(self, obj) -> bool:
        if obj is None:
            return False
        return obj.is_organization_manager or obj.is_company_executive

    def has_add_permission(self, request):
        """Members cannot be added via the admin interface. They are created automatically when a user is created."""
        return False

    def has_import_permission(self, request):
        return self.has_change_permission(request)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        readonly_fields.append("user")
        readonly_fields.append("is_organization_manager")
        login_member = request.user.member
        if not (login_member.is_accounting_staff or login_member.is_sys_staff):
            readonly_fields.append("join_date")

        if not login_member.is_sys_staff:
            readonly_fields.append("organization")

        if login_member != obj:
            readonly_fields.append("email")
            readonly_fields.append("work_pattern")

        return readonly_fields


# print Method Resolution Order of MemberAdmin class
# print([cls.__name__ for cls in MemberAdmin.__mro__])
# Find which class in the MRO actually owns the active has_add_permission implementation
# print(MemberAdmin.has_add_permission.__qualname__)
