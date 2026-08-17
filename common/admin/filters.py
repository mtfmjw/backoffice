from django.contrib.admin import SimpleListFilter
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django.db import connection
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


class SimpleOrganizationFilter(SimpleListFilter):
    title = _("Organization")
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        sql = Organization.get_whole_organization_tree_sql()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        return [(str(org_id), f"{'  ' * depth}{name}") for org_id, name, depth in rows]

    def queryset(self, request, queryset):
        value = self.value()

        if value is not None:
            below_organization_ids_sql = Organization.get_sub_department_ids_sql(int(value))
            if queryset.model._meta.model_name == "organization":
                return queryset.filter(id__in=RawSQL(below_organization_ids_sql, []))
            elif hasattr(queryset.model, "organization"):
                return queryset.filter(organization__id__in=RawSQL(below_organization_ids_sql, []))
            elif hasattr(queryset.model, "member"):
                return queryset.filter(member__organization_id__in=RawSQL(below_organization_ids_sql, []))

        return queryset


class OrganizationFilter(SimpleOrganizationFilter):
    title = _("Organization")
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        if model_admin.can_view_all_organizations(request):
            choices = super().lookups(request, model_admin)
        elif model_admin.can_view_organization(request):
            root_organization_id = request.user.member.organization_id
            sql = Organization.get_sub_organization_tree_sql(root_organization_id)
            with connection.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
            choices = [(str(org_id), f"{'  ' * depth}{name}") for org_id, name, depth in rows]

        return choices if "choices" in locals() else []
