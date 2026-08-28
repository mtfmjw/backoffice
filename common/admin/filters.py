from django.contrib.admin import SimpleListFilter
from django.contrib.admin.filters import RelatedOnlyFieldListFilter
from django.utils.translation import gettext_lazy as _

from common.models.organization import Organization

# 2020年からのカレンダーを表示する


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

        return choices if "choices" in locals() else []
