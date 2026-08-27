from typing import ClassVar

from django.contrib.admin import display
from django.db.models.expressions import RawSQL
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportMixin
from import_export.formats.base_formats import CSV
from import_export.forms import ExportForm

from common.admin.filters import OrganizationFilter
from common.models import Organization
from common.utils import convert2localtime


class AuthorizedModelAdminMixin(ImportExportMixin):
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
        return super().has_view_permission(request, obj) and self.model.is_authorized(request.user)

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
        return self.has_add_permission(request) and self.has_change_permission(request)

    def has_export_permission(self, request):
        """Override to check if the user has permission to export data."""
        return self.has_view_permission(request)


class BaseModelAdminMixin(AuthorizedModelAdminMixin):
    """Base ModelAdmin for common models with soft delete and audit fields"""

    readonly_fields = ("valid_flag", "created_by", "created_at", "updated_by", "updated_at")
    list_display = ("valid_flag", "updated_by", "display_updated_at")
    list_filter = ("valid_flag",)

    class Media:
        css: ClassVar[dict[str, tuple[str, ...]]] = {"all": ("admin/css/admin_extra.css",)}

    @display(description=_("Update Time"))
    def display_updated_at(self, obj):
        updated_at = convert2localtime(obj.updated_at)
        return updated_at.strftime("%Y/%m/%d %H:%M:%S")

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

    def get_readonly_fields(self, request, obj=None):
        # 1. Fetch base/parent readonly fields safely
        parent_readonly = super().get_readonly_fields(request, obj)

        # 2. Define audit fields required for your custom fieldset
        audit_readonly = ("valid_flag", "created_by", "created_at", "updated_by", "updated_at")

        # 3. Merge without creating duplicates
        return tuple(set(parent_readonly) | set(audit_readonly))

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


class OrgScopedModelAdminMixin(BaseModelAdminMixin):
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

            below_organization_ids_sql = Organization.get_below_organization_ids_sql(accessible_organization.id)
            if hasattr(self.model, "organization"):
                return qs.filter(organization_id__in=RawSQL(below_organization_ids_sql, []))
            elif hasattr(self.model, "member"):
                return qs.filter(member__organization_id__in=RawSQL(below_organization_ids_sql, []))
        else:
            # 自分のデータのみ見れる
            if self.model._meta.model_name == "member":
                return qs.filter(user=request.user)
            elif hasattr(self.model, "member"):
                return qs.filter(member__user=request.user)
        return qs
