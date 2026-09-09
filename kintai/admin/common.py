from dateutil.relativedelta import relativedelta
from django.contrib.admin import SimpleListFilter
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _


class MonthFilter(SimpleListFilter):
    title = _("Month")
    parameter_name = "month"
    field_name = "month"
    start_month = localdate().replace(day=1) + relativedelta(months=-5)
    end_month = localdate().replace(day=1) + relativedelta(months=1)

    def lookups(self, request, model_admin):
        choices = []
        current_month = self.end_month
        while current_month >= self.start_month:
            val = current_month.strftime("%Y-%m")
            label = current_month.strftime("%Y年%m月")
            choices.append((val, label))
            current_month -= relativedelta(months=1)
        return choices

    def queryset(self, request, queryset):
        value = self.value()
        if value is None:
            return queryset
        try:
            year, month = map(int, value.split("-"))
            return queryset.filter(**{f"{self.field_name}__year": year, f"{self.field_name}__month": month})
        except (ValueError, AttributeError):
            return queryset
