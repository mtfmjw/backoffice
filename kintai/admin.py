from inspect import Attribute
from time import timezone

from dateutil.relativedelta import relativedelta
from django.contrib import admin
from django.contrib.admin import display
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.instance_loaders import CachedInstanceLoader
from import_export.widgets import DateWidget

from backoffice.admin import admin_site
from kintai.models import Holiday, WorkPattern

CALENDAR_START_YEAR = 2020  # カレンダーの開始年を設定


def show_duration(start_time, end_time):
    if start_time and end_time:
        start = start_time.strftime("%H:%M")
        end = end_time.strftime("%H:%M")
        return f"{start} - {end}"
    return "-"


class YearlyFilter(admin.SimpleListFilter):
    title = "対象年"
    parameter_name = "year"

    def lookups(self, request, model_admin):
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


class MonthlyFilter(admin.SimpleListFilter):
    title = "対象月"
    parameter_name = "month"

    def lookups(self, request, model_admin):
        """
        今月を中心に、前後の月選択肢（YYYY-MM形式）を降順（新しい月が上）で生成します。
        例: 2027-08, 2027-07 ... 2026-08 (今月) ... 2025-08
        """
        today = localdate()
        current_first = today.replace(day=1)

        # 未来12ヶ月〜過去12ヶ月（計25ヶ月分）の選択肢を降順で生成
        choices = []
        for i in range(1, -12, -1):
            m_date = current_first + relativedelta(months=i)
            val = m_date.strftime("%Y-%m")
            label = m_date.strftime("%Y年%m月")
            choices.append((val, label))

        choices.append(("all", "全期間"))
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        today = timezone.localdate()

        # 1. 初期表示（パラメータなし） -> 来月1日〜1年間（12ヶ月分）に絞り込み
        if value is None:
            # 来月第1日 (例: 2026-09-01)
            next_month_start = today.replace(day=1) + relativedelta(months=1)
            # 1年後の月末 (例: 2027-08-31)
            one_year_later_end = (next_month_start + relativedelta(years=1)) - relativedelta(days=1)

            return queryset.filter(date__range=(next_month_start, one_year_later_end))

        # 2. 「全期間」選択時 -> 絞り込みなし
        if value == "all":
            return queryset

        # 3. 特定の「年月 (例: 2026-09)」選択時 -> その1ヶ月間のみ表示
        try:
            year, month = map(int, value.split("-"))
            return queryset.filter(date__year=year, date__month=month)
        except (ValueError, Attribute):
            return queryset


class HolidayResource(resources.ModelResource):
    date = fields.Field(column_name="date", attribute="date", widget=DateWidget(format="%Y/%m/%d"))

    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        instance_loader_class = CachedInstanceLoader

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


@admin.register(Holiday, site=admin_site)
class HolidayAdmin(ImportExportModelAdmin):
    resource_class = HolidayResource
    list_display = ("date", "type", "name")
    list_filter = (YearlyFilter,)
    search_fields = ("date", "name")
    fieldsets = (
        (
            None,
            {
                "fields": ("date", "type", "name"),
            },
        ),
    )


class WorkPatternResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        report_skipped = True
        use_bulk = True
        instance_loader_class = CachedInstanceLoader

        model = WorkPattern
        fields = (
            "name",
            "start_time",
            "end_time",
            "lunch_break_start_time",
            "lunch_break_end_time",
            "break1_start_time",
            "break1_end_time",
            "break2_start_time",
            "break2_end_time",
            "break3_start_time",
            "break3_end_time",
            "break4_start_time",
            "break4_end_time",
            "break5_start_time",
            "break5_end_time",
        )
        import_id_fields = ("name",)


@admin.register(WorkPattern, site=admin_site)
class WorkPatternAdmin(ImportExportModelAdmin):
    resource_class = WorkPatternResource
    list_display = (
        "name",
        "working_duration",
        "lunch_break_duration",
        "break1_duration",
        "break2_duration",
        "break3_duration",
        "break4_duration",
        "break5_duration",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    ("start_time", "end_time"),
                    ("lunch_break_start_time", "lunch_break_end_time"),
                    ("break1_start_time", "break1_end_time"),
                    ("break2_start_time", "break2_end_time"),
                    ("break3_start_time", "break3_end_time"),
                    ("break4_start_time", "break4_end_time"),
                    ("break5_start_time", "break5_end_time"),
                ),
            },
        ),
    )

    @display(description=_("勤務時間"))
    def working_duration(self, obj):
        return show_duration(obj.start_time, obj.end_time)

    @display(description=_("昼休憩"))
    def lunch_break_duration(self, obj):
        return show_duration(obj.lunch_break_start_time, obj.lunch_break_end_time)

    @display(description=_("休憩１"))
    def break1_duration(self, obj):
        return show_duration(obj.break1_start_time, obj.break1_end_time)

    @display(description=_("休憩２"))
    def break2_duration(self, obj):
        return show_duration(obj.break2_start_time, obj.break2_end_time)

    @display(description=_("休憩３"))
    def break3_duration(self, obj):
        return show_duration(obj.break3_start_time, obj.break3_end_time)

    @display(description=_("休憩４"))
    def break4_duration(self, obj):
        return show_duration(obj.break4_start_time, obj.break4_end_time)

    @display(description=_("休憩５"))
    def break5_duration(self, obj):
        return show_duration(obj.break5_start_time, obj.break5_end_time)
