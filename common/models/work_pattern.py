from django.db import models
from django.utils.translation import gettext_lazy as _


class WorkPattern(models.Model):
    """就業パターンマスタ（通常・シフト・フレックスなど）"""

    name = models.CharField(_("Work Pattern Name"), max_length=100, unique=True)
    start_time = models.TimeField(_("Standard Start Time"), default="09:30")
    end_time = models.TimeField(_("Standard End Time"), default="18:00")

    lunch_break_start_time = models.TimeField(_("Lunch Break Start Time"), default="12:00")
    lunch_break_end_time = models.TimeField(_("Lunch Break End Time"), default="13:00")
    standard_work_time = models.TimeField(_("Standard Working Time"), default="07:30", null=True, blank=True)
    break1_start_time = models.TimeField(_("Break 1 Start Time"), default="18:00", null=True, blank=True)
    break1_end_time = models.TimeField(_("Break 1 End Time"), default="18:30", null=True, blank=True)
    break2_start_time = models.TimeField(_("Break 2 Start Time"), default="20:00", null=True, blank=True)
    break2_end_time = models.TimeField(_("Break 2 End Time"), default="20:30", null=True, blank=True)
    break3_start_time = models.TimeField(_("Break 3 Start Time"), default="22:30", null=True, blank=True)
    break3_end_time = models.TimeField(_("Break 3 End Time"), default="22:45", null=True, blank=True)
    break4_start_time = models.TimeField(_("Break 4 Start Time"), default="03:00", null=True, blank=True)
    break4_end_time = models.TimeField(_("Break 4 End Time"), default="03:30", null=True, blank=True)
    break5_start_time = models.TimeField(_("Break 5 Start Time"), default="09:00", null=True, blank=True)
    break5_end_time = models.TimeField(_("Break 5 End Time"), default="09:30", null=True, blank=True)

    class Meta:
        db_table = "work_pattern"
        verbose_name = _("Work Pattern")
        verbose_name_plural = _("Work Patterns")
        ordering = ("start_time",)

    def __str__(self):
        return self.name

    def get_standard_work_minutes(self):
        """Return the default standard work time in minutes."""
        if self.standard_work_time is not None:
            return self.standard_work_time.hour * 60 + self.standard_work_time.minute
        else:
            # If standard_work_time is None, calculate it from start_time and end_time
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            if end_minutes <= start_minutes:
                end_minutes += 24 * 60  # Adjust for overnight shifts

            lunch_break_minutes = 0
            if self.lunch_break_start_time and self.lunch_break_end_time:
                lunch_start_minutes = self.lunch_break_start_time.hour * 60 + self.lunch_break_start_time.minute
                lunch_end_minutes = self.lunch_break_end_time.hour * 60 + self.lunch_break_end_time.minute
                if lunch_end_minutes <= lunch_start_minutes:
                    lunch_end_minutes += 24 * 60  # Adjust for overnight breaks
                lunch_break_minutes = lunch_end_minutes - lunch_start_minutes
            return end_minutes - start_minutes - lunch_break_minutes
