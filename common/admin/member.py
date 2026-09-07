from functools import partial

from django import forms
from django.contrib import admin
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.db import connection
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

    list_display = ("full_name", "user", "email", "organization", "is_organization_manager", "work_pattern", "join_date", "paid_leave_available")
    list_filter = (SimpleOrganizationFilter,)
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "organization__code",
        "organization__name",
    )
    list_select_related = ("user", "organization")
    fields = (("user", "email"), ("organization", "is_organization_manager"), ("join_date", "paid_leave_available"), "work_pattern")

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
        if not request.user.member.is_attendance_management_staff:
            readonly_fields.append("join_date")
            readonly_fields.append("paid_leave_available")

        if not request.user.member.is_system_info_staff:
            readonly_fields.append("organization")

        if request.user.member != obj:
            readonly_fields.append("email")
            readonly_fields.append("work_pattern")

        return readonly_fields

    # Use *args and **kwargs to avoid positional argument mismatch with mixins
    def get_form(self, request, obj=None, *args, **kwargs):
        # 1. Call super() passing *args and **kwargs dynamically
        FormClass = super().get_form(request, obj, *args, **kwargs)

        # 2. Use partial to inject 'request' without altering class instantiation arguments
        return partial(FormClass, request=request)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.user.member.is_attendance_management_staff:
            object = self.get_object(request, object_id)
            if object is None:
                return super().changeform_view(request, object_id, form_url, extra_context)

            if object.join_date is None:
                show_apply_button = True
            else:
                # １年以内に入社した場合にのみ年次有休日数取得ボタンを表示する
                today = timezone.localdate()
                one_year_ago = today.replace(year=today.year - 1)
                show_apply_button = object.join_date <= today and object.join_date >= one_year_ago

            if show_apply_button:
                extra_context = extra_context or {}
                extra_context["show_apply_button"] = show_apply_button
                extra_context["apply_button_name"] = "_yearly_paid_leave"
                extra_context["apply_button_label"] = _("Calculate Yearly Paid Leave Days")
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        """Override save_model to enforce custom save logic if needed."""
        if "_yearly_paid_leave" in request.POST and obj is not None and obj.join_date is not None:
            with connection.cursor() as cursor:
                # Implement the logic to calculate yearly paid leave days here
                cursor.execute("""select get_paid_leave_days(%s,%s)""", [obj.join_date, timezone.localdate()])
                obj.paid_leave_available = cursor.fetchone()[0]
        super().save_model(request, obj, form, change)

    def response_change(self, request, obj):
        # 1. Check if your custom button was clicked
        if "_yearly_paid_leave" in request.POST:
            # Perform any custom logic/side-effects here
            self.message_user(request, _("Yearly paid leave days calculated for {obj}. Saved successfully!").format(obj=obj))

            # 2. Tell Django to treat this like '_continue'
            # By adding '_continue' to request.POST, super().response_change redirect back to change form
            request.POST = request.POST.copy()
            request.POST["_continue"] = "1"

        return super().response_change(request, obj)


# print Method Resolution Order of MemberAdmin class
# print([cls.__name__ for cls in MemberAdmin.__mro__])
# Find which class in the MRO actually owns the active has_add_permission implementation
# print(MemberAdmin.has_add_permission.__qualname__)
