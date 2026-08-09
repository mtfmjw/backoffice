from django.contrib import admin
from django.utils.timezone import localdate
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import DateWidget

from backoffice.admin import admin_site
from kintai.models import Holiday

CALENDAR_START_YEAR = 2020  # カレンダーの開始年を設定


class HolidayResource(resources.ModelResource):
    date = fields.Field(column_name="date", attribute="date", widget=DateWidget(format="%Y/%m/%d"))

    class Meta:
        skip_unchanged = True
        report_skipped = True

        model = Holiday
        fields = ("date", "name")
        import_id_fields = ("date",)

    def before_import_row(self, row, **kwargs):
        """
        Intercepts each row before processing.
        If 'type' is missing in the CSV, inject a default value.
        """
        if "type" not in row or not row["type"]:
            row["type"] = Holiday.Type.NATIONAL_HOLIDAY

        super().before_import_row(row, **kwargs)


class YearlyHolidayFilter(admin.SimpleListFilter):
    title = "対象年"
    parameter_name = "year"

    def lookups(self, request, model_admin):
        """
        今年を中心に [去年, 今年, 来年] の選択肢を動的に生成します。
        必要に応じて前後の年数を増やすことも可能です。
        """
        start_year = CALENDAR_START_YEAR  # カレンダーの開始年
        end_year = localdate().year + 1  # 将来の年数を制限する場合はここで設定
        years = list(range(end_year, start_year, -1))

        choices = [(str(y), f"{y}年") for y in years]
        choices.append(("all", "全期間"))

        return choices

    def queryset(self, request, queryset):
        value = self.value()
        current_year = localdate().year

        # 初期表示（パラメータなし） -> 今年（1年分）のみ表示
        if value is None:
            return queryset.filter(date__year=current_year)

        # 「全期間」選択時 -> 全て表示
        if value == "all":
            return queryset.filter(date__year__gte=CALENDAR_START_YEAR)

        # 特定の「年」選択時 -> その1年分のみ表示
        if value.isdigit():
            return queryset.filter(date__year=int(value))

        return queryset


@admin.register(Holiday, site=admin_site)
class HolidayAdmin(ImportExportModelAdmin):
    resource_class = HolidayResource
    use_bulk = True
    list_display = ("date", "type", "name")
    list_filter = (YearlyHolidayFilter,)
    search_fields = ("date", "name")
    fieldsets = (
        (
            None,
            {
                "fields": ("date", "type", "name"),
            },
        ),
    )
