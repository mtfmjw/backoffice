from import_export import resources

from common.models import Prefecture

from .base import MemberScopedAdmin


class PrefectureResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Prefecture
        fields = ("code", "name")
        import_id_fields = ("code",)


# @admin.register(Prefecture, site=admin_site)
class PrefectureAdmin(MemberScopedAdmin):
    resource_class = PrefectureResource
    list_display = ("name", "code")
    list_display_links = None
    search_fields = ("name",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_import_permission(self, request):
        return self.has_change_permission(request)

    def has_export_permission(self, request):
        return False


# print Method Resolution Order of Prefecture class
# print([cls.__name__ for cls in PrefectureAdmin.__mro__])
# Find which class in the MRO actually owns the active has_add_permission implementation
# print(PrefectureAdmin.has_change_permission.__qualname__)
