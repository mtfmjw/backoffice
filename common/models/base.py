from datetime import timedelta

from django.db import models
from django.utils.timezone import datetime, localdate
from django.utils.translation import gettext_lazy as _

from common.middleware import get_current_user


class BaseModel(models.Model):
    valid_flag = models.BooleanField(default=True, verbose_name=_("Valid"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    created_by = models.CharField(max_length=150, verbose_name=_("Created by"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    updated_by = models.CharField(max_length=150, verbose_name=_("Updated by"))

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and user.is_authenticated:
            if not self.pk:
                self.created_by = user.get_username()
            self.updated_by = user.get_username()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.valid_flag = False
        self.save()


def get_duration_in_minutes(start_time, end_time):
    """2つの時刻の差を分単位で返す"""
    base_start_date = localdate()
    if end_time < start_time:
        # 日を跨ぐ場合は、end_timeを翌日に設定
        base_end_date = base_start_date + timedelta(days=1)
    else:
        base_end_date = base_start_date

    return (datetime.combine(base_end_date, end_time) - datetime.combine(base_start_date, start_time)).seconds // 60
