from django.contrib.admin import SimpleListFilter
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
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


class YearFilter(SimpleListFilter):
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

    def choices(self, changelist):
        """
        Override choices to strip out the default 'All' option.
        """
        # Call the parent generator to get all choices
        all_choices = list(super().choices(changelist))

        # The first item (index 0) in all_choices is always the 'All' link.
        # Returning all_choices[1:] strips it out.
        return all_choices[1:]
