from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import BaseModel
from common.models.work_pattern import WorkPattern


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
    def get_sub_department_ids_sql(cls, root_organization_id: int) -> str:
        """
        SQL snippet using a recursive CTE to return IDs of root_organization_id
        and all its descendants.
        """
        return f"""
        WITH RECURSIVE organization_tree AS (
            SELECT id FROM organization WHERE id = {root_organization_id}
            UNION ALL
            SELECT d.id 
            FROM organization d
            INNER JOIN organization_tree dt ON d.parent_id = dt.id
        )
        SELECT id FROM organization_tree
    """

    @staticmethod
    def get_sub_organization_tree_sql(root_dept_id):
        """
        Returns a recursive CTE SQL query that calculates hierarchy depth
        and sort order path based on organization code.
        """
        return f"""
                    WITH RECURSIVE dept_tree AS (
                        SELECT 
                            id, 
                            name, 
                            code, 
                            parent_id, 
                            0 AS depth,
                            CAST(code AS VARCHAR(1000)) AS sort_path
                        FROM organization
                        WHERE id = {int(root_dept_id)} AND valid_flag = TRUE
                        UNION ALL
                        SELECT 
                            o.id, 
                            o.name, 
                            o.code, 
                            o.parent_id, 
                            dt.depth + 1 AS depth,
                            CAST(dt.sort_path || '/' || o.code AS VARCHAR(1000)) AS sort_path
                        FROM organization o
                        INNER JOIN dept_tree dt ON o.parent_id = dt.id
                        WHERE o.valid_flag = TRUE
                    )
                    SELECT id, name, depth FROM dept_tree ORDER BY sort_path
                """

    @staticmethod
    def get_whole_organization_tree_sql():
        """
        Returns a recursive CTE SQL query that calculates hierarchy depth
        and sort order path based on organization code.
        """
        return """
                    WITH RECURSIVE dept_tree AS (
                        SELECT 
                            id, 
                            name, 
                            code, 
                            parent_id, 
                            0 AS depth,
                            CAST(code AS VARCHAR(1000)) AS sort_path
                        FROM organization
                        WHERE parent_id is null AND valid_flag = TRUE
                        UNION ALL
                        SELECT 
                            o.id, 
                            o.name, 
                            o.code, 
                            o.parent_id, 
                            dt.depth + 1 AS depth,
                            CAST(dt.sort_path || '/' || o.code AS VARCHAR(1000)) AS sort_path
                        FROM organization o
                        INNER JOIN dept_tree dt ON o.parent_id = dt.id
                        WHERE o.valid_flag = TRUE
                    )
                    SELECT id, name, depth FROM dept_tree ORDER BY sort_path
                """
