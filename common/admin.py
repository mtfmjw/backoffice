from typing import ClassVar

from django.contrib import admin
from django.contrib.admin import display
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ImportMixin
from import_export.instance_loaders import CachedInstanceLoader
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.models import Member, Municipality, Organization, Postcode, Prefecture


class BaseModelAdmin(admin.ModelAdmin):
    """Base ModelAdmin for common models with soft delete and audit fields"""

    base_fields_columns = 2
    readonly_fields = ("valid_flag", "created_by", "created_at", "updated_by", "updated_at")
    list_display = ("valid_flag", "updated_by", "updated_at")
    list_filter = ("valid_flag",)

    class Media:
        css: ClassVar[dict[str, tuple[str, ...]]] = {"all": ("admin/admin_extra.css",)}

    def get_search_help_text(self):
        """Generate help text for search_fields based on model verbose names, supporting __ lookups."""
        help_texts = []
        for field_name in getattr(self, "search_fields", []):
            try:
                # Strip prefix characters (^, -)
                clean_name = field_name.lstrip("^-")

                # Handle __ lookups (e.g., user__username)
                parts = clean_name.split("__")
                model = self.model
                verbose_name = None

                for part in parts:
                    field = model._meta.get_field(part)
                    verbose_name = str(field.verbose_name)
                    # If it's a relation field, follow it
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


class PrefectureResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Prefecture
        fields = ("code", "name")
        import_id_fields = ("code",)


@admin.register(Prefecture, site=admin_site)
class PrefectureAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = PrefectureResource
    use_bulk = True
    list_display = ("name", "code")
    search_fields = ("code", "name")
    fieldsets = (
        (
            None,
            {
                "fields": ("code", "name"),
            },
        ),
    )

    def has_add_permission(self, request):
        # Hide the "Add" button
        return False

    def has_delete_permission(self, request):
        # Hide the "Delete" button
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing the list, but prevent editing
        return False

    # Disable the edit screen by removing the link to it
    list_display_links = None


class PrefectureFilter(RelatedOnlyFieldListFilter):
    """都道府県の表示順を並び替えるフィルター"""

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        # Use an actual model field name for the display value (e.g. 'name'),
        # not the verbose_name which is a human-readable string like 'ID'.
        display_field = "name"
        # Fallback to the PK field name if 'name' does not exist on the related model
        if not hasattr(field.related_model, "name"):
            display_field = field.related_model._meta.pk.name
        self.lookup_choices = list(field.related_model.objects.order_by("code").values_list("pk", display_field))


class MunicipalityResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        batch_size = 20000
        instance_loader_class = CachedInstanceLoader

        model = Municipality
        import_id_fields = ("code",)
        fields = ("code", "name", "name_kana", "prefecture")

    # 🔑 ForeignKey mapping: Look up Prefecture model by its 'code' field
    prefecture = fields.Field(
        attribute="prefecture",
        column_name="prefecture_code",  # The exact column header in your CSV file
        widget=ForeignKeyWidget(Prefecture, field="code"),
    )


@admin.register(Municipality, site=admin_site)
class MunicipalityAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = MunicipalityResource
    list_display = ("prefecture__name", "code", "name")
    search_fields = ("prefecture__name", "code", "name")
    list_select_related = ()
    list_filter = (("prefecture", PrefectureFilter),)
    fieldsets = (
        (
            None,
            {
                "fields": ("prefecture", "code", "name"),
            },
        ),
    )

    def has_add_permission(self, request):
        # Hide the "Add" button
        return False

    def has_delete_permission(self, request):
        # Hide the "Delete" button
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing the list, but prevent editing
        return False

    # Disable the edit screen by removing the link to it
    list_display_links = None


class PostcodeResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        instance_loader_class = CachedInstanceLoader

        model = Postcode
        import_id_fields = ("postcode",)
        fields = ("postcode", "municipality", "town_name", "town_name_kana")

    # 変数名をフィールド名と変え、column_name と attribute を明示的に指定
    postcode_field = fields.Field(
        column_name="postcode",  # CSV/Excelファイルのヘッダー名
        attribute="postcode",  # Djangoモデルのフィールド名
    )
    prefecture = fields.Field(column_name="prefecture_code", readonly=True)
    # 🔑 ForeignKey mapping: Look up Municipality model by its 'code' field
    municipality = fields.Field(
        attribute="municipality",
        column_name="municipality_code",  # The exact column header in your CSV file
        widget=ForeignKeyWidget(Municipality, field="code"),
    )


@admin.register(Postcode, site=admin_site)
class PostcodeAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = PostcodeResource
    list_display = ("postcode", "municipality")
    search_fields = ("postcode", "municipality", "town_name")
    list_select_related = ("municipality",)
    list_filter = (("municipality__prefecture", PrefectureFilter),)
    fieldsets = (
        (
            None,
            {
                "fields": ("postcode", "municipality", "town_name", "town_name_kana"),
            },
        ),
    )

    def has_add_permission(self, request):
        # Hide the "Add" button
        return False

    def has_delete_permission(self, request):
        # Hide the "Delete" button
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing the list, but prevent editing
        return False

    # Disable the edit screen by removing the link to it
    list_display_links = None


@admin.register(Organization, site=admin_site)
class OrganizationAdmin(BaseModelAdmin):
    list_display = ("code", "name", "parent") + BaseModelAdmin.list_display
    search_fields = ("code", "name")
    list_select_related = ("parent",)
    fieldsets = (
        (
            None,
            {
                "fields": ("code", "name", "parent"),
            },
        ),
    )


@admin.register(Member, site=admin_site)
class MemberAdmin(BaseModelAdmin):
    has_add_permission = lambda self, request: False
    readonly_fields = ("user",) + BaseModelAdmin.readonly_fields
    list_display = ("full_name", "user", "email", "organization") + BaseModelAdmin.list_display
    search_fields = ("user__username", "user__first_name", "user__last_name", "organization__code", "organization__name")
    list_select_related = ("user", "organization")
    list_filter = ("organization",) + BaseModelAdmin.list_filter
    fieldsets = (
        (
            None,
            {
                "fields": (("user", "email"), ("organization", "manager_flag")),
            },
        ),
    )

    @display(description=_("Full Name"))
    def full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}"
