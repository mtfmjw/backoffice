from typing import ClassVar

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import display
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _
from import_export import widgets
from import_export.admin import ImportExportMixin
from import_export.formats.base_formats import CSV
from import_export.forms import ExportForm

from common.admin.filters import OrganizationFilter
from common.const import ApproveStatus
from common.models import Organization
from common.models.base import ConcurrencyError
from common.models.member import get_user_full_name
from common.utils import convert2localtime, convert2str

User = get_user_model()


class CommonImportResourceMixin:
    """Mixin to add import functionality to a ModelAdmin using django-import-export."""

    def get_compare_ignored_fields(self):
        return []

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if not self._meta.skip_unchanged or self._meta.skip_diff or import_validation_errors:
            return False
        for field in self.get_import_fields():
            if field.column_name in self.get_compare_ignored_fields():
                continue
            # For fields that are models.fields.related.ManyRelatedManager
            # we need to compare the results
            if isinstance(field.widget, widgets.ManyToManyWidget):
                # #1437 - handle m2m field not present in import file
                if field.column_name not in row.keys():  # noqa: SIM118
                    continue
                # m2m instance values are taken from the 'row' because they
                # have not been written to the 'instance' at this point
                instance_values = list(field.clean(row))
                original_values = [] if original.pk is None else list(field.get_value(original).all())
                if len(instance_values) != len(original_values):
                    return False

                if sorted(v.pk for v in instance_values) != sorted(v.pk for v in original_values):
                    return False
            elif field.get_value(instance) != field.get_value(original):
                return False
        return True


class CommonImportExportMixin(ImportExportMixin):
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
    export_template_name = "admin/common/export.html"
    import_template_name = "admin/common/import.html"

    def has_import_permission(self, request):
        permission = self.has_add_permission(request) and self.has_change_permission(request)
        return permission

    def has_export_permission(self, request):
        """Override to check if the user has permission to export data."""
        return self.has_view_permission(request)

    def get_changelist_url(self, request):
        """
        直前に適用されていたフィルター（クエリパラメータ）を取得して復元したURLを返します。
        """
        # 直前のチェンジリストのフィルター情報を取得
        preserved_filters = request.GET.get("_changelist_filters")
        changelist_url = super().get_changelist_url(request)

        if preserved_filters:
            return f"{changelist_url}?{preserved_filters}"
        return changelist_url

    def get_export_filename(self, request, queryset, file_format):
        date_str = convert2localtime(timezone.now()).strftime("%Y_%m_%d")
        filename = f"{self.model.__name__}_{date_str}.{file_format.get_extension()}"
        return filename


class MemberScopedAdminMixin:
    """This mixin provides methods to check if a user is authorized to perform import/export actions in the Django admin interface."""

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

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_return"] = True
        extra_context["show_save_and_add_another"] = False
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    @display(description=_("Belong To"))
    def belong(self, obj) -> str:
        if obj.member is None or getattr(obj.member, "organization", None) is None:
            return "-"
        return obj.member.organization.name


class MemberScopedAdmin(CommonImportExportMixin, MemberScopedAdminMixin, admin.ModelAdmin):
    """Base ModelAdmin for common models with member-scoped access control and import/export functionality."""


class RowScopedAdminMixin(MemberScopedAdminMixin):
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


class RowScopedAdmin(CommonImportExportMixin, RowScopedAdminMixin, admin.ModelAdmin):
    """Base ModelAdmin for common models with row-scoped access control, import/export functionality, and organization filtering."""


class BaseModelAdminMixin:
    """Base ModelAdmin for common models with soft delete and audit fields"""

    class Media:
        css: ClassVar[dict[str, tuple[str, ...]]] = {"all": ("admin/css/admin_extra.css",)}

    @display(description=_("Updated by"))
    def display_updated_by(self, obj):
        return get_user_full_name(obj.updated_by) if obj.updated_by else "-"

    @display(description=_("Updated at"))
    def display_updated_at(self, obj):
        return convert2str(obj.updated_at) if obj.updated_at else "-"

    @display(description=_("Audit Info"))
    def audit_info(self, obj):
        """Display audit information for the object, including created_by, created_at, updated_by, and updated_at."""

        if obj is None:
            return ""

        # 作成者情報
        created_by = get_user_full_name(obj.created_by)
        created_at = convert2str(obj.created_at)
        audit_info = f"{_('Created by')}：{created_by}　{_('Created at')}：{created_at}　"

        # 更新者情報
        updated_by = get_user_full_name(obj.updated_by)
        updated_at = convert2str(obj.updated_at)
        audit_info += f"　{_('Updated by')}：{updated_by}　{_('Updated at')}：{updated_at}"
        return audit_info

    def action_checkbox(self, obj):
        return format_html('<input type="checkbox" name="_selected_action" value="{}:{}" class="action-select">', obj.pk, obj.version)

    # Re-apply the select-all header toggle
    # action_checkbox.short_description = format_html('<input type="checkbox" id="action-toggle">')

    def get_actions(self, request):
        actions = super().get_actions(request)

        # 1. Remove the default built-in delete action
        if "delete_selected" in actions:
            del actions["delete_selected"]

        # 2. Dynamically register your custom action (e.g., check delete permissions)
        delete_perm = f"{self.opts.app_label}.delete_{self.opts.model_name}"
        if request.user.has_perm(delete_perm):
            actions["delete_selected_with_lock"] = (
                self.delete_selected_with_lock.__func__,
                "delete_selected_with_lock",
                "Delete selected items",
            )
            actions["undelete_selected_with_lock"] = (
                self.undelete_selected_with_lock.__func__,
                "undelete_selected_with_lock",
                "Undelete selected items",
            )

        return actions

    # Intercept response_action to clean request.POST before Django validates PKs
    def response_action(self, request, queryset):
        raw_selected = request.POST.getlist("_selected_action")

        # Store composite pairs on request object for your action methods to use
        request.version_pairs = []
        clean_pks = []

        for pair in raw_selected:
            if ":" in pair:
                request.version_pairs.append(pair)
                pk, __ = pair.split(":", 1)
                clean_pks.append(pk)
            else:
                clean_pks.append(pair)

        # Mutate POST data temporarily so Django's internal queryset filtering receives valid PK integers
        post_data = request.POST.copy()
        post_data.setlist("_selected_action", clean_pks)
        request.POST = post_data

        # Let Django proceed with standard action dispatching
        return super().response_action(request, queryset)

    # Action method defined directly on ModelAdmin
    def delete_selected_with_lock(self, request, queryset):
        success_count, conflict_count, skipped_count = self.toggle_valid_flag(request, False)

        if success_count > 0:
            self.message_user(
                request,
                _("Successfully deleted %(success_count)d item(s).") % {"success_count": success_count},
                messages.SUCCESS,
            )

        if conflict_count > 0:
            self.message_user(
                request,
                _("Concurrency Conflict: %(conflict_count)d item(s) could not be deleted because they were modified by another user.")
                % {"conflict_count": conflict_count},
                messages.ERROR,
            )

        if skipped_count > 0:
            self.message_user(
                request,
                _("Skipped: %(skipped_count)d item(s) could not be deleted because they were already deleted.") % {"skipped_count": skipped_count},
                messages.ERROR,
            )

    def undelete_selected_with_lock(self, request, queryset):
        success_count, conflict_count, skipped_count = self.toggle_valid_flag(request, True)

        if success_count > 0:
            self.message_user(
                request,
                _("Successfully undeleted %(success_count)d item(s).") % {"success_count": success_count},
                messages.SUCCESS,
            )

        if conflict_count > 0:
            self.message_user(
                request,
                _("Concurrency Conflict: %(conflict_count)d item(s) could not be undeleted because they were modified by another user.")
                % {"conflict_count": conflict_count},
                messages.ERROR,
            )

        if skipped_count > 0:
            self.message_user(
                request,
                _("Skipped: %(skipped_count)d item(s) could not be undeleted because they were already undeleted.")
                % {"skipped_count": skipped_count},
                messages.ERROR,
            )

    def toggle_valid_flag(self, request, valid_flag) -> tuple[int, int, int]:
        selected_pairs = getattr(request, "version_pairs", [])

        if not selected_pairs:
            self.message_user(request, _("No items selected."), messages.ERROR)
            return 0, 0, 0

        success_count = 0
        conflict_count = 0
        skipped_count = 0

        for pair in selected_pairs:
            try:
                pk, ui_version = map(int, pair.split(":"))
            except (ValueError, AttributeError):
                continue

            field_dict = {}
            field_dict["updated_by"] = request.user.username
            field_dict["updated_at"] = timezone.now()
            field_dict["valid_flag"] = valid_flag
            field_dict["version"] = ui_version + 1

            # Delete only if both ID and version match current DB state
            is_exists = self.model.objects.filter(pk=pk, version=ui_version, valid_flag=valid_flag).exists()
            if is_exists:
                skipped_count += 1
                continue

            deleted_count = self.model.objects.filter(pk=pk, version=ui_version).update(**field_dict)

            if deleted_count > 0:
                success_count += 1
            else:
                conflict_count += 1

        return success_count, conflict_count, skipped_count

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

    def get_readonly_fields(self, request, obj=None):
        """Add audit fields to readonly_fields for all descendants."""

        readonly_fields = list(super().get_readonly_fields(request, obj))

        if "audit_info" not in readonly_fields:
            readonly_fields.append("audit_info")

        if "version" in readonly_fields:
            readonly_fields.remove("version")  # Must not be read-only for HiddenInput to render

        for f in ["valid_flag", "created_by", "created_at", "updated_by", "updated_at"]:
            if f not in readonly_fields:
                readonly_fields.append(f)
        return readonly_fields

    def get_fields(self, request, obj=None):
        """Add version andaudit fields to fields for all descendants."""
        fields = list(super().get_fields(request, obj))

        if self.has_change_permission(request, obj) and fields and "version" not in fields:
            fields.append("version")

        if fields and "audit_info" not in fields:
            fields.append("audit_info")
        return fields

    def get_fieldsets(self, request, obj=None):
        """Add version and audit fields to fieldsets for all descendants."""
        fieldsets = list(super().get_fieldsets(request, obj))

        if self.has_change_permission(request, obj) and fieldsets and not any("version" in opts.get("fields", []) for _, opts in fieldsets):
            name, opts = fieldsets[0]
            updated_fields = tuple(list(opts.get("fields", [])) + ["version"])
            fieldsets[0] = (name, {**opts, "fields": updated_fields})

        if fieldsets and not any("audit_info" in opts.get("fields", []) for _, opts in fieldsets):
            fieldsets.append((None, {"fields": ("audit_info",)}))
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        """Override to hide the version field in the form for all descendants."""

        form = super().get_form(request, obj, **kwargs)
        if "version" in form.base_fields:
            form.base_fields["version"].widget = forms.HiddenInput()
        return form

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Override to handle ConcurrencyError and display a user-friendly message."""

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
            obj.created_by = request.user.username

        obj.updated_by = request.user.username
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Override to perform a soft delete by toggling the valid_flag instead of deleting the record."""
        obj.valid_flag = not obj.valid_flag
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


class ImportBaseModelResourceMixin(CommonImportResourceMixin):
    """Mixin to add import functionality to a ModelAdmin using django-import-export."""

    def get_compare_ignored_fields(self):
        ignored_fields = super().get_compare_ignored_fields()
        ignored_fields.extend(["created_by", "created_at", "updated_by", "updated_at", "version"])
        return ignored_fields

    def before_import_row(self, row, **kwargs):
        """Set created_by and updated_by fields based on the current user."""
        if "created_by" not in row or not row["created_by"]:
            row["created_by"] = kwargs.get("user").username
        if "updated_by" not in row or not row["updated_by"]:
            row["updated_by"] = kwargs.get("user").username
        if "valid_flag" not in row or not row["valid_flag"]:
            row["valid_flag"] = True
        super().before_import_row(row, **kwargs)


class MemberScopedBaseModelAdmin(CommonImportExportMixin, MemberScopedAdminMixin, BaseModelAdminMixin, admin.ModelAdmin):
    """Base ModelAdmin for common models with member-scoped access control, soft delete, and audit fields."""


class RowScopedBaseModelAdmin(CommonImportExportMixin, RowScopedAdminMixin, BaseModelAdminMixin, admin.ModelAdmin):
    """Base ModelAdmin for common models with row-scoped access control, soft delete, and audit fields."""


class ApprovedModelAdminMixin:
    """Mixin to add approval functionality to a ModelAdmin."""

    @display(description=_("Audit Info"))
    def audit_info(self, obj):
        """Display audit information for the object, including created_by, created_at, updated_by, and updated_at."""
        if obj and obj.applied_at is not None:
            # 申請者情報
            applied_by = get_user_full_name(obj.applied_by) or "-"
            applied_at = convert2str(obj.applied_at)
            audit_info = f"{_('Applied by')}：{applied_by}　{_('Applied at')}：{applied_at}　"
            # 承認者情報
            approved_by = get_user_full_name(obj.approved_by) or "-"
            approved_at = convert2str(obj.approved_at)
            audit_info += f"　{_('Approved by')}：{approved_by}　{_('Approved at')}：{approved_at}　"
            # 確定者情報
            confirmed_by = get_user_full_name(obj.confirmed_by) or "-"
            confirmed_at = convert2str(obj.confirmed_at)
            audit_info += f"　{_('Confirmed by')}：{confirmed_by}　{_('Confirmed at')}：{confirmed_at}"

            return audit_info
        return super().audit_info(obj)

    def get_list_display(self, request):
        """Add audit fields to list_display for all descendants."""
        list_display = list(super().get_list_display(request))
        for f in ["valid_flag", "applied_by", "applied_at", "approved_by", "approved_at", "confirmed_by", "confirmed_at"]:
            if f not in list_display:
                list_display.append(f)
        return tuple(list_display)

    def get_list_filter(self, request):
        """Add audit fields to list_filter for all descendants."""
        list_filter = list(super().get_list_filter(request))
        list_filter.insert(0, "approve_status")
        return tuple(list_filter)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        if object_id is None:
            extra_context["show_apply_button"] = True
            extra_context["apply_button_name"] = "_apply"
            extra_context["apply_button_label"] = _("Apply")
        else:
            extra_context["show_save_and_add_another"] = False

            obj = self.get_object(request, object_id)
            if obj.is_editable_by(request.user):
                extra_context["show_apply_button"] = True
                extra_context["show_save"] = True
                extra_context["show_save_and_continue"] = True
                extra_context["show_reject_button"] = False
                extra_context["next"] = False
                extra_context["apply_button_name"] = "_apply"
                extra_context["apply_button_label"] = _("Apply")
            else:
                extra_context["adminform_class"] = "is-readonly-form"

                extra_context["show_save"] = False
                extra_context["show_save_and_continue"] = False
                extra_context["next"] = True
                if obj.approve_status in [ApproveStatus.REJECTED, ApproveStatus.CONFIRMED]:
                    extra_context["show_apply_button"] = False
                    extra_context["show_reject_button"] = False
                else:
                    login_user = request.user
                    if obj.approve_status == ApproveStatus.APPLIED:
                        extra_context["show_apply_button"] = obj.is_approvable_by(login_user)
                        extra_context["show_reject_button"] = obj.is_approvable_by(login_user)
                        extra_context["apply_button_name"] = "_approve"
                        extra_context["apply_button_label"] = _("Approve")
                        extra_context["save_and_add_label"] = _("Approve and Go to Next")
                    elif obj.approve_status == ApproveStatus.APPROVED:
                        extra_context["show_apply_button"] = obj.is_confirmable_by(login_user)
                        extra_context["show_reject_button"] = obj.is_confirmable_by(login_user)
                        extra_context["apply_button_name"] = "_confirm"
                        extra_context["apply_button_label"] = _("Confirm")
                        extra_context["save_and_add_label"] = _("Confirm and Go to Next")

        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if "_apply" in request.POST:
            obj.approve_status = ApproveStatus.APPLIED
            obj.applied_by = request.user.username
            obj.applied_at = localtime()
            super().save_model(request, obj, form, change)
        elif "_approve" in request.POST:
            obj.approve_status = ApproveStatus.APPROVED
            obj.approved_by = request.user.username
            obj.approved_at = localtime()
            obj.save(update_fields=["approve_status", "approved_by", "approved_at"])
        elif "_confirm" in request.POST:
            obj.approve_status = ApproveStatus.CONFIRMED
            obj.confirmed_by = request.user.username
            obj.confirmed_at = localtime()
            obj.save(update_fields=["approve_status", "confirmed_by", "confirmed_at"])
        elif "_reject" in request.POST:
            obj.approve_status = ApproveStatus.REJECTED
            obj.save(update_fields=["approve_status"])
        elif "_reapply" in request.POST:
            obj.approve_status = ApproveStatus.APPLIED
            obj.applied_by = request.user.username
            obj.applied_at = localtime()
            super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)


class ApprovedBaseModelAdmin(ApprovedModelAdminMixin, RowScopedBaseModelAdmin):
    """Base ModelAdmin for row-scoped models with approval functionality."""
