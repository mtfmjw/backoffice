from django.db import models
from django.utils.translation import gettext_lazy as _

from common.models.base import BaseModel
from common.models.work_pattern import WorkPattern


class Organization(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Organization Code"))
    name = models.CharField(max_length=255, verbose_name=_("Organization Name"))
    work_pattern = models.ForeignKey(WorkPattern, on_delete=models.DO_NOTHING, null=True, blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children", verbose_name=_("Parent Organization")
    )

    class Meta:
        db_table = "organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")

    def __str__(self):
        return self.name
