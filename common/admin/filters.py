from django.contrib.admin import SimpleListFilter
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django.db.models.expressions import RawSQL
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from common.models.organization import Organization

# 2020年からのカレンダーを表示する
CALENDAR_START_YEAR = 2020


class PrefectureFilter(RelatedOnlyFieldListFilter):
    """都道府県の表示順を並び替えるフィルター"""

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        display_field = "name"
        if not hasattr(field.related_model, "name"):
            display_field = field.related_model._meta.pk.name
        self.lookup_choices = list(field.related_model.objects.order_by("code").values_list("pk", display_field))


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
            queryset.filter(date__year=current_year)
        if value == "all":
            queryset.filter(date__year__gte=CALENDAR_START_YEAR)
        if value.isdigit():
            queryset.filter(date__year=int(value))
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


class OrganizationFilter(SimpleListFilter):
    title = _("Organization")
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        if request.user.is_superuser or request.user.member.is_company_executive() or request.user.member.is_system_info_staff():
            choices = Organization.objects.filter(valid_flag=True).order_by("code").values_list("id", "name")
        elif request.user.member.is_organization_manager():
            root_organization_id = request.user.member.organization_id
            below_organization_ids_sql = Organization.get_sub_department_ids_sql(root_organization_id)
            choices = (
                Organization.objects.filter(valid_flag=True, id__in=RawSQL(below_organization_ids_sql, []))
                .order_by("code")
                .values_list("id", "name")
            )
        return choices if "choices" in locals() else []

    def queryset(self, request, queryset):
        value = self.value()

        if value is not None:
            below_organization_ids_sql = Organization.get_sub_department_ids_sql(int(value))
            if hasattr(queryset.model, "organization"):
                return queryset.filter(organization__id__in=RawSQL(below_organization_ids_sql, []))
            elif hasattr(queryset.model, "member"):
                return queryset.filter(member__organization_id__in=RawSQL(below_organization_ids_sql, []))

        return queryset
