from dateutil.relativedelta import relativedelta
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django.utils import timezone
from django.utils.timezone import localdate

from common.admin.base import CALENDAR_START_YEAR


class PrefectureFilter(RelatedOnlyFieldListFilter):
    """都道府県の表示順を並び替えるフィルター"""

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        display_field = "name"
        if not hasattr(field.related_model, "name"):
            display_field = field.related_model._meta.pk.name
        self.lookup_choices = list(field.related_model.objects.order_by("code").values_list("pk", display_field))


class YearlyFilter(SimpleListFilter):
    title = "対象年"
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
        if value == "all":
            return queryset.filter(date__year__gte=CALENDAR_START_YEAR)
        if value.isdigit():
            return queryset.filter(date__year=int(value))
        return queryset


class MonthlyFilter(SimpleListFilter):
    title = "対象月"
    parameter_name = "month"

    def lookups(self, request, model_admin):
        today = localdate()
        current_first = today.replace(day=1)
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
        if value is None:
            next_month_start = today.replace(day=1) + relativedelta(months=1)
            one_year_later_end = (next_month_start + relativedelta(years=1)) - relativedelta(days=1)
            return queryset.filter(date__range=(next_month_start, one_year_later_end))
        if value == "all":
            return queryset
        try:
            year, month = map(int, value.split("-"))
            return queryset.filter(date__year=year, date__month=month)
        except (ValueError, AttributeError):
            return queryset
