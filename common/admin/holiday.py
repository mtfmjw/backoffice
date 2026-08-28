from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.widgets import DateWidget

from backoffice.admin import admin_site
from common.models import Holiday

from .base import MemberScopedAdmin

CALENDAR_START_YEAR = 2020


class YearFilter(SimpleListFilter):
    title = _("Year")
    parameter_name = "year"

    def lookups(self, request, model_admin):
        start_year = CALENDAR_START_YEAR
        end_year = localdate().year + 1
        years = list(range(end_year, start_year, -1))
        choices = [(str(y), f"{y}年") for y in years]
        choices.append(("all", "全期間"))
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        current_year = localdate().year

        if value is None:
            return queryset.filter(date__year=current_year)
        elif value == "all":
            return queryset.filter(date__year__gte=CALENDAR_START_YEAR)
        elif value.isdigit():
            return queryset.filter(date__year=int(value))
        return queryset

    def choices(self, changelist):
        """
        Override choices to strip out the default 'All' option.
        """
        # Call the parent generator to get all choices
        all_choices = list(super().choices(changelist))

        # The first item (index 0) in all_choices is always the 'All' link.
        # Returning all_choices[1:] strips it out.
        return all_choices[1:]


class HolidayResource(resources.ModelResource):
    date = fields.Field(column_name="date", attribute="date", widget=DateWidget(format="%Y/%m/%d"))

    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        batch_size = 20000

        model = Holiday
        fields = ("date", "name")
        export_order = ("date", "name")
        import_id_fields = ("date",)

    def before_import_row(self, row, **kwargs):
        if "type" not in row or not row["type"]:
            row["type"] = Holiday.Type.NATIONAL_HOLIDAY
        super().before_import_row(row, **kwargs)


@admin.register(Holiday, site=admin_site)
class HolidayAdmin(MemberScopedAdmin):
    resource_class = HolidayResource

    list_display = ("date", "type", "name")
    list_filter = (YearFilter,)
    search_fields = ("type", "name")
    fields = (("date", "type"), "name")
