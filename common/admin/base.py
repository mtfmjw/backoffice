from typing import ClassVar

from django.contrib import admin

CALENDAR_START_YEAR = 2020


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


def show_duration(start_time, end_time):
    if start_time and end_time:
        start = start_time.strftime("%H:%M")
        end = end_time.strftime("%H:%M")
        return f"{start} - {end}"
    return "-"
