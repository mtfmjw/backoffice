from django.contrib import admin
from import_export import fields, resources
from import_export.widgets import DateWidget, ForeignKeyWidget

from backoffice.admin import admin_site
from common.models import TransportationCompany, TransportationLine
from common.models.transport import TransportationStation

from .base import MemberScopedAdmin


@admin.register(TransportationCompany, site=admin_site)
class TransportationCompanyAdmin(MemberScopedAdmin):
    list_display = ("company_cd", "company_name", "company_name_k", "company_type", "e_status")
    search_fields = ("company_name", "company_name_k")
    list_filter = ("company_type", "e_status")
    list_display_links = ("company_name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_import_permission(self, request):
        return True

    def has_export_permission(self, request):
        return False


class TransportationLineResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = TransportationLine
        import_id_fields = ("line_cd",)

    company = fields.Field(
        attribute="company",
        column_name="company_cd",
        widget=ForeignKeyWidget(TransportationCompany, field="company_cd"),
    )


@admin.register(TransportationLine, site=admin_site)
class TransportationLineAdmin(MemberScopedAdmin):
    resource_class = TransportationLineResource
    list_display = ("line_cd", "company", "line_name", "line_name_k", "e_status")
    search_fields = ("line_name", "line_name_k", "company__company_name")
    list_filter = ("e_status",)
    list_display_links = ("line_name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_import_permission(self, request):
        return True

    def has_export_permission(self, request):
        return False


class NullableDateWidget(DateWidget):
    def clean(self, value, row=None, *args, **kwargs):
        # Strip whitespace and check for zero-date strings or empty values
        if isinstance(value, str):
            value = value.strip()
            if value in ("0000-00-00", "0000/00/00", "0", ""):
                return None
        return super().clean(value, row=row, *args, **kwargs)


class TransportationStationResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = TransportationStation
        import_id_fields = ("station_cd",)

    line = fields.Field(
        attribute="line",
        column_name="line_cd",
        widget=ForeignKeyWidget(TransportationLine, field="line_cd"),
    )

    open_ymd = fields.Field(
        attribute="open_ymd",
        column_name="open_ymd",
        widget=NullableDateWidget(),
    )

    close_ymd = fields.Field(
        attribute="close_ymd",
        column_name="close_ymd",
        widget=NullableDateWidget(),
    )


@admin.register(TransportationStation, site=admin_site)
class TransportationStationAdmin(MemberScopedAdmin):
    resource_class = TransportationStationResource
    list_display = ("station_cd", "station_name", "line", "e_status")
    search_fields = ("station_name", "station_name_k", "station_name_r")
    list_filter = ("e_status",)
    list_display_links = ("station_name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_import_permission(self, request):
        return True

    def has_export_permission(self, request):
        return False
