from django.contrib import admin
from import_export import resources

from common.models import Prefecture

from .base import AuthorizedModelAdminMixin


class PrefectureResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Prefecture
        fields = ("code", "name")
        import_id_fields = ("code",)


# @admin.register(Prefecture, site=admin_site)
class PrefectureAdmin(AuthorizedModelAdminMixin, admin.ModelAdmin):
    resource_class = PrefectureResource
    list_display = ("name", "code")
    list_display_links = None
    search_fields = ("name",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_export_permission(self, request):
        return False
