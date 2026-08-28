from typing import ClassVar

from django import forms
from django.contrib import messages
from django.contrib.admin import display
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportMixin
from import_export.formats.base_formats import CSV
from import_export.forms import ExportForm

from common.admin.filters import OrganizationFilter
from common.models import Organization
from common.models.base import ConcurrencyError
from common.utils import convert2localtime


class RowPermissionModelAdminAdminMixin(ImportExportMixin):
    """This mixin provides methods to check if a user is authorized to perform import/export actions in the Django admin interface."""

    class DirectExportForm(ExportForm):
        """
        Export form that completely removes the field-selection checkboxes,
        forcing django-import-export to use the resource's predefined fields.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Remove the export_fields selection box
            if "export_fields" in self.fields:
                del self.fields["export_fields"]

    import_formats = (CSV,)
    export_formats = (CSV,)
    export_form_class = DirectExportForm

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

    def has_view_permission(self, request, obj=None):
        """Override to check if the user has permission to view the object."""
        permission = super().has_view_permission(request, obj) and self.model.is_authorized(request.user)
        return permission

    def has_add_permission(self, request):
        """Override to check if the user has permission to add a new object."""
        return super().has_add_permission(request) and self.model.is_authorized(request.user)

    def has_change_permission(self, request, obj=None):
        """Override to check if the user has permission to change the object."""
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return self.model.is_authorized(request.user)
        return obj.is_editable_by(request.user)

    def has_delete_permission(self, request, obj=None):
        """Override to check if the user has permission to delete the object."""
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return self.model.is_authorized(request.user)
        return obj.is_deletable_by(request.user)

    def has_import_permission(self, request):
        permission = self.has_add_permission(request) and self.has_change_permission(request)
        return permission

    def has_export_permission(self, request):
        """Override to check if the user has permission to export data."""
        return self.has_view_permission(request)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_return"] = True
        extra_context["show_save_and_add_another"] = False
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


class BaseModelAdminMixin(RowPermissionModelAdminAdminMixin):
    """Base ModelAdmin for common models with soft delete and audit fields"""

    class Media:
        css: ClassVar[dict[str, tuple[str, ...]]] = {"all": ("admin/css/admin_extra.css",)}

    @display(description=_("Update Time"))
    def display_updated_at(self, obj):
        updated_at = convert2localtime(obj.updated_at)
        return updated_at.strftime("%Y/%m/%d %H:%M:%S")

    def get_readonly_fields(self, request, obj=None):
        """Add audit fields to readonly_fields for all descendants."""

        readonly_fields = list(super().get_readonly_fields(request, obj))
        for f in ["valid_flag", "created_by", "created_at", "updated_by", "updated_at"]:
            if f not in readonly_fields:
                readonly_fields.append(f)
        return readonly_fields

    def get_list_display(self, request):
        """Add audit fields to list_display for all descendants."""
        list_display = list(super().get_list_display(request))
        for f in ["valid_flag", "updated_by", "display_updated_at"]:
            if f not in list_display:
                list_display.append(f)
        return tuple(list_display)

    def get_list_filter(self, request):
        """Add valid_flag to list_filter for all descendants."""
        list_filter = list(super().get_list_filter(request))
        for f in ["valid_flag"]:
            if f not in list_filter:
                list_filter.append(f)
        return tuple(list_filter)

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if "version" not in fields:
            fields.append("version")
        return fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if fieldsets and not any("version" in opts.get("fields", []) for _, opts in fieldsets):
            name, opts = fieldsets[0]
            updated_fields = tuple(list(opts.get("fields", [])) + ["version"])
            fieldsets[0] = (name, {**opts, "fields": updated_fields})
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "version" in form.base_fields:
            form.base_fields["version"].widget = forms.HiddenInput()
        return form

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except ConcurrencyError:
            self.message_user(
                request, _("This record was modified by another user while you were editing it. Your changes were not saved."), level=messages.ERROR
            )
            return HttpResponseRedirect(request.path)

    def save_model(self, request, obj, form, change):
        """Override to set created_by and updated_by fields based on the current user."""
        if not obj.pk:
            obj.created_by = request.user

        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Override to perform a soft delete by toggling the valid_flag instead of deleting the record."""
        if obj.valid_flag:
            obj.valid_flag = False
        else:
            obj.valid_flag = True

        obj.updated_by = request.user.username
        obj.save(update_fields=["valid_flag", "updated_by"])

    def delete_queryset(self, request, queryset):
        """Override to perform a soft delete on a queryset by toggling the valid_flag instead of deleting the records."""
        for obj in queryset:
            if obj.valid_flag:
                obj.valid_flag = False
            else:
                obj.valid_flag = True

            obj.updated_by = request.user.username
            obj.save(update_fields=["valid_flag", "updated_by"])


class MemberScopedModelAdminMixin(BaseModelAdminMixin):
    """This mixin provides methods to check if a user with a member profile can access a model instance in the Django admin interface."""

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))

        if self.model.is_all_organizations_accessible(request.user) or self.model.get_accessible_top_organization(request.user) is not None:
            filters.insert(0, OrganizationFilter)

        return tuple(filters)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if self.model.is_all_organizations_accessible(request.user):
            return qs
        elif self.model.get_accessible_top_organization(request.user) is not None:
            # 組織の管理者は自組織メンバーのデータのみ見れる
            accessible_organization = self.model.get_accessible_top_organization(request.user)
            if accessible_organization is None:
                return qs.none()

            descendants = Organization.get_descendant_organizations(accessible_organization)
            if hasattr(self.model, "organization"):
                return qs.filter(organization_id__in=[o[0] for o in descendants])
            elif hasattr(self.model, "member"):
                return qs.filter(member__organization_id__in=[o[0] for o in descendants])
        else:
            # 自分のデータのみ見れる
            if self.model._meta.model_name == "member":
                return qs.filter(user=request.user)
            elif hasattr(self.model, "member"):
                return qs.filter(member__user=request.user)
        return qs
