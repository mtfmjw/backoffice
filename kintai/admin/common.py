from dateutil.relativedelta import relativedelta
from django.contrib.admin import SimpleListFilter
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _


class MonthFilter(SimpleListFilter):
    title = _("Month")
    parameter_name = "month"

    def lookups(self, request, model_admin):
        current_first_day = localdate().replace(day=1)
        choices = []
        for i in range(1, -5, -1):
            m_date = current_first_day + relativedelta(months=i)
            val = m_date.strftime("%Y-%m")
            label = m_date.strftime("%Y年%m月")
            choices.append((val, label))
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        if value is None:
            return queryset
        try:
            year, month = map(int, value.split("-"))
            return queryset.filter(month__year=year, month__month=month)
        except (ValueError, AttributeError):
            return queryset


class KintaiModelAdminMixin:
    """Base ModelAdmin mixin for Kintai models with common functionality."""
