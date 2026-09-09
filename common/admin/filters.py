from django.contrib.admin import SimpleListFilter
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy as _

from common.models.organization import Organization


class YearFilter(SimpleListFilter):
    title = _("Year")
    parameter_name = "year"
    start_year = 2020
    end_year = localdate().year + 1
    field_name = "date"

    def lookups(self, request, model_admin):
        years = list(range(self.end_year, self.start_year - 1, -1))
        choices = [(str(y), f"{y}年") for y in years]
        choices.append(("all", "全期間"))
        return choices

    def queryset(self, request, queryset):
        value = self.value()

        if value is None:
            start_date = localdate().replace(month=1, day=1)
            end_date = start_date.replace(year=start_date.year + 1)
            return queryset.filter(**{f"{self.field_name}__gte": start_date, f"{self.field_name}__lt": end_date})
        elif value == "all":
            start_date = localdate().replace(year=self.start_year, month=1, day=1)
            return queryset.filter(**{f"{self.field_name}__gte": start_date})
        elif value.isdigit():
            start_date = localdate().replace(year=int(value), month=1, day=1)
            end_date = start_date.replace(year=start_date.year + 1)
            return queryset.filter(**{f"{self.field_name}__gte": start_date, f"{self.field_name}__lt": end_date})
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


class PrefectureFilter(RelatedOnlyFieldListFilter):
    """都道府県の表示順を並び替えるフィルター"""

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        display_field = "name"
        if not hasattr(field.related_model, "name"):
            display_field = field.related_model._meta.pk.name
        self.lookup_choices = list(field.related_model.objects.order_by("code").values_list("pk", display_field))


class SimpleOrganizationFilter(SimpleListFilter):
    title = _("Organization")
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        return Organization.get_descendant_organization_tree()

    def queryset(self, request, queryset):
        value = self.value()

        if value is not None:
            descendants = Organization.get_descendant_organizations(Organization.objects.get(id=int(value)))
            organization_ids = [org_id for org_id, __, __ in descendants]
            if queryset.model._meta.model_name == "organization":
                return queryset.filter(id__in=organization_ids)
            elif hasattr(queryset.model, "organization"):
                return queryset.filter(organization__id__in=organization_ids)
            elif hasattr(queryset.model, "member"):
                return queryset.filter(member__organization_id__in=organization_ids)

        return queryset


class OrganizationFilter(SimpleOrganizationFilter):
    title = _("Organization")
    parameter_name = "organization"

    def lookups(self, request, model_admin):
        if model_admin.model.is_all_organizations_accessible(request.user):
            choices = super().lookups(request, model_admin)
        else:
            accessible_organization = model_admin.model.get_accessible_top_organization(request.user)
            if accessible_organization is None:
                return []
            choices = Organization.get_descendant_organization_tree(accessible_organization)

        choices.append(("individual", _("Individual")))
        return choices if "choices" in locals() else []

    def queryset(self, request, queryset):
        value = self.value()

        if value == "individual" and hasattr(queryset.model, "member"):
            return queryset.filter(member=request.user.member)
        return super().queryset(request, queryset)
