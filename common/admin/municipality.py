from django.contrib import admin
from import_export import fields, resources
from import_export.instance_loaders import CachedInstanceLoader
from import_export.widgets import ForeignKeyWidget

from common.admin.base import AuthorizedModelAdminMixin
from common.models import Municipality, Prefecture

from .filters import PrefectureFilter


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

    prefecture = fields.Field(
        attribute="prefecture",
        column_name="prefecture_code",
        widget=ForeignKeyWidget(Prefecture, field="code"),
    )


# @admin.register(Municipality, site=admin_site)
class MunicipalityAdmin(AuthorizedModelAdminMixin, admin.ModelAdmin):
    resource_class = MunicipalityResource
    list_display = ("prefecture", "code", "name")
    search_fields = ("prefecture__name", "code", "name")
    list_select_related = ()
    list_filter = (("prefecture", PrefectureFilter),)
    list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_export_permission(self, request):
        return False
