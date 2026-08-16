from datetime import datetime
from typing import ClassVar

from django.contrib.admin import display
from django.utils.translation import gettext_lazy as _

from common.admin.filters import OrganizationFilter
from common.const import KINTAI_MANAGER_GROUP_NAME, MASTER_MANAGER_GROUP_NAME, SYSTEM_MANAGER_GROUP_NAME


class CommonAdminMixin:
    """This mixin provides common functionality for Django admin classes, including methods for generating search help text and customizing the changelist view."""

    def get_search_help_text(self):
        """Generate help text for search_fields based on model verbose names, supporting __ lookups."""
        help_texts = []
        for field_name in getattr(self, "search_fields", []):
            try:
                clean_name = field_name.lstrip("^-")
                parts = clean_name.split("__")
                model = self.model
                verbose_name = None

                for part in parts:
                    field = model._meta.get_field(part)
                    verbose_name = str(field.verbose_name)
                    if hasattr(field, "related_model"):
                        model = field.related_model

                if verbose_name:
                    help_texts.append(verbose_name)
                else:
                    help_texts.append(field_name)
            except Exception:  # noqa: BLE001
                help_texts.append(field_name)
        return ", ".join(help_texts) if help_texts else ""

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["search_help_text"] = self.get_search_help_text()
        return super().changelist_view(request, extra_context)


class BaseModelAdminMixin(CommonAdminMixin):
    """Base ModelAdmin for common models with soft delete and audit fields"""

    readonly_fields = ("valid_flag", "created_by", "created_at", "updated_by", "updated_at")
    list_display = ("valid_flag", "updated_by", "display_updated_at")
    list_filter = ("valid_flag",)

    class Media:
        css: ClassVar[dict[str, tuple[str, ...]]] = {"all": ("admin/admin_extra.css",)}

    @display(description=_("Update Time"))
    def display_updated_at(self, obj):
        return obj.updated_at.strftime("%Y/%m/%d %H:%M:%S")

    def delete_model(self, request, obj):
        if not obj.valid_flag:
            obj.valid_flag = True
            obj.save(update_fields=["valid_flag", "updated_by", "updated_at"])
        else:
            obj.delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if not obj.valid_flag:
                obj.valid_flag = True
                obj.save(update_fields=["valid_flag", "updated_by", "updated_at"])
            else:
                obj.delete()

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        audit_section = (
            None,
            {
                "fields": ("valid_flag", ("created_by", "created_at"), ("updated_by", "updated_at")),
            },
        )
        fieldsets = list(fieldsets)
        fieldsets.append(audit_section)
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        fieldsets = self.get_fieldsets(request, obj)
        all_fields = []
        for name, opts in fieldsets:
            for f in opts.get("fields", []):
                if isinstance(f, (list, tuple)):
                    all_fields.extend(f)
                else:
                    all_fields.append(f)
        kwargs["fields"] = all_fields
        return super().get_form(request, obj, **kwargs)


class MasterImportExportPermissionMixin:
    """This mixin provides import and export permissions for superusers and members of specific groups."""

    def has_import_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name__in=(MASTER_MANAGER_GROUP_NAME, SYSTEM_MANAGER_GROUP_NAME)).exists()

    def has_export_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name__in=(MASTER_MANAGER_GROUP_NAME, SYSTEM_MANAGER_GROUP_NAME)).exists()


class OrganizationFilterMixin:
    """This mixin provides a method to filter querysets based on the user's organization."""

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))

        filters.insert(0, OrganizationFilter)

        if hasattr(self, "list_filter"):
            filters.extend(self.list_filter)

        return tuple(filters)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if (
            request.user.is_superuser
            or request.user.groups.filter(name=KINTAI_MANAGER_GROUP_NAME).exists()
            or request.user.groups.filter(name=SYSTEM_MANAGER_GROUP_NAME).exists()
        ):
            # superuser、勤怠管理グループのメンバーは全員のデータが見れる
            return qs
        elif request.user.member.manager_flag:
            # 組織の管理者は自組織メンバーのデータのみ見れる
            if hasattr(self.model, "organization"):
                return qs.filter(organization=request.user.member.organization)
            elif hasattr(self.model, "member") and request.user.member and request.user.member.manager_flag:
                return qs.filter(member__organization=request.user.member.organization)
        else:
            # 自分のデータのみ見れる
            if self.model._meta.model_name == "member":
                return qs.filter(user=request.user)
            elif hasattr(self.model, "member"):
                return qs.filter(member__user=request.user)


def show_duration(start_time: datetime, end_time: datetime):
    """Show duration in HH:MM - HH:MM format."""
    if start_time and end_time:
        start = start_time.strftime("%H:%M")
        end = end_time.strftime("%H:%M")
        return f"{start} - {end}"
    return "-"
