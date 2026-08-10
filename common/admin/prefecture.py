from django.contrib import admin
from import_export import resources
from import_export.admin import ImportMixin

from backoffice.admin import admin_site
from common.models import Prefecture


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
        return False

    def has_delete_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    list_display_links = None
