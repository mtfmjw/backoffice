from django.contrib import admin
from django.db import connection
from import_export import resources
from import_export.admin import ImportMixin
from import_export.formats.base_formats import CSV

from backoffice.admin import admin_site
from common.models import Postcode, PostcodeImport

from .base import CommonAdminMixin, MasterImportExportPermissionMixin
from .filters import PrefectureFilter


class PostcodeResource(resources.ModelResource):
    class Meta:
        # skip_diff = True  # preview画面で差分を表示しないようにする
        # skip_html_diff = True
        use_bulk = True
        batch_size = 50000

        model = PostcodeImport
        import_id_fields = ("postcode", "municipality_code", "town_name", "town_name_kana")
        fields = ("postcode", "municipality_code", "town_name", "town_name_kana")

    def get_or_init_instance(self, instance_loader, row):
        """
        Overrides the entire lookup routine.
        Returns (new_instance, is_created) WITHOUT hitting the database.
        """
        instance = self.init_instance(row)
        return instance, True

    def before_import(self, dataset, **kwargs):
        """
        Runs before the import process starts.
        """
        # CRITICAL: Only execute during the actual import, NOT during the dry-run/preview step
        with connection.cursor() as cursor:
            # 1. Clear the temporary table
            cursor.execute("truncate table tmp_postcode_import")

    def after_import(self, dataset, result, **kwargs):
        """
        Runs after the import process completes.
        """
        # CRITICAL: Only execute during the actual import, NOT during the dry-run/preview step
        with connection.cursor() as cursor:
            # 1. Standard raw SQL query
            cursor.execute("""
                merge into postcode main
                using (
                    select
                        p.postcode,
                        m.id as municipality_id,
                        p.town_name,
                        p.town_name_kana
                    from tmp_postcode_import p
                    left join municipality m on p.municipality_code = m.code
                ) as source
                on (main.postcode = source.postcode
                and main.municipality_id = source.municipality_id
                and main.town_name = source.town_name
                and main.town_name_kana = source.town_name_kana)
                when not matched then
                    insert (postcode, municipality_id, town_name, town_name_kana)
                    values (source.postcode, source.municipality_id, source.town_name, source.town_name_kana)
                when matched then
                    update set
                        municipality_id = source.municipality_id,
                        town_name = source.town_name,
                        town_name_kana = source.town_name_kana
            """)

        super().after_import(dataset, result, **kwargs)


@admin.register(Postcode, site=admin_site)
class PostcodeAdmin(CommonAdminMixin, MasterImportExportPermissionMixin, ImportMixin, admin.ModelAdmin):
    resource_class = PostcodeResource
    formats = (CSV,)
    list_display = ("postcode", "municipality", "town_name", "town_name_kana")
    search_fields = ("postcode", "municipality__name", "town_name")
    list_select_related = ("municipality",)
    list_filter = (("municipality__prefecture", PrefectureFilter),)
    list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
