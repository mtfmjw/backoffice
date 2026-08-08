from django.contrib import admin
from import_export import resources
from import_export.admin import ImportMixin

from backoffice.admin import admin_site
from kintai.models import Holiday


class HolidayResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Holiday
        fields = ("date", "type", "name")
        import_id_fields = ("date",)


@admin.register(Holiday, site=admin_site)
class HolidayAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = HolidayResource
    use_bulk = True
    list_display = ("date", "type", "name")
    search_fields = ("date", "name")
    fieldsets = (
        (
            None,
            {
                "fields": ("date", "type", "name"),
            },
        ),
    )
