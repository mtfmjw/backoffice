from __future__ import annotations

from django.db import connection, models
from django.utils.translation import gettext_lazy as _

from .base import BaseModel
from .work_pattern import WorkPattern


class Organization(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Organization Code"))
    name = models.CharField(max_length=255, verbose_name=_("Organization Name"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True, verbose_name=_("Work Pattern"))
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children", verbose_name=_("Parent Organization")
    )

    class Meta:
        db_table = "organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")

    def __str__(self):
        return self.name

    @classmethod
    def get_descendant_organizations(cls, current_organization: Organization | None = None) -> list[tuple[int, str, int]]:
        """
        Returns a list of descendant organizations for the given organization.
        If the current_organization is None, it returns all organizations.
        """

        sql = """
                    WITH RECURSIVE organization_tree AS (
                        SELECT 
                            id, 
                            name, 
                            code, 
                            parent_id, 
                            0 AS depth,
                            CAST(code AS VARCHAR(1000)) AS sort_path
                        FROM organization
                        WHERE ((%s::integer IS NULL AND parent_id IS NULL AND valid_flag = TRUE)
                            OR (id = %s::integer AND valid_flag = TRUE))
                            AND valid_flag = TRUE
                        UNION ALL
                        SELECT 
                            o.id, 
                            o.name, 
                            o.code, 
                            o.parent_id, 
                            dt.depth + 1 AS depth,
                            CAST(dt.sort_path || '/' || o.code AS VARCHAR(1000)) AS sort_path
                        FROM organization o
                        INNER JOIN organization_tree dt ON o.parent_id = dt.id
                        WHERE o.valid_flag = TRUE
                    )
                    SELECT id, name, depth
                    FROM organization_tree tree
                    ORDER BY sort_path
                """
        current_organization_id = current_organization.id if current_organization else None
        with connection.cursor() as cursor:
            cursor.execute(sql, [current_organization_id, current_organization_id])
            rows = cursor.fetchall()
        return rows

    @classmethod
    def get_descendant_organization_tree(cls, current_organization: Organization | None = None) -> list[tuple[str, str]]:
        """
        Returns a recursive CTE SQL query that calculates hierarchy depth
        and sort order path based on organization code.
        """
        descendants = cls.get_descendant_organizations(current_organization)
        return [(str(org_id), f"{'--' * depth}{name}") for org_id, name, depth in descendants]

    def get_ancestor_organizations(self):
        """
        Returns a list of organizations from the current organization up to the root organization.
        The list is ordered from the current organization to the root organization.
        """
        current_organization = self
        ancestors = [current_organization]
        while current_organization.parent is not None:
            ancestors.append(current_organization.parent)
            current_organization = current_organization.parent
        return ancestors
