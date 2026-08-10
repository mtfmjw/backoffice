from django.contrib import admin
from import_export import fields, resources
from import_export.admin import ImportMixin
from import_export.instance_loaders import CachedInstanceLoader
from import_export.widgets import ForeignKeyWidget

from backoffice.admin import admin_site
from common.models import Municipality, Postcode

from .filters import PrefectureFilter


class PostcodeResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        instance_loader_class = CachedInstanceLoader

        model = Postcode
        import_id_fields = ("postcode",)
        fields = ("postcode", "municipality", "town_name", "town_name_kana")

    postcode_field = fields.Field(
        column_name="postcode",
        attribute="postcode",
    )
    prefecture = fields.Field(column_name="prefecture_code", readonly=True)
    municipality = fields.Field(
        attribute="municipality",
        column_name="municipality_code",
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
        return False

    def has_delete_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    list_display_links = None
