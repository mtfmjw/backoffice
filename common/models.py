from django.conf import settings
from django.db import models
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


class Organization(BaseModel):
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Organization Code"))
    name = models.CharField(max_length=255, verbose_name=_("Organization Name"))
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent Organization"),
    )

    class Meta:
        db_table = "organization"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")

    def __str__(self):
        return self.name


class Member(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member",
        verbose_name=_("Employee Number"),
    )
    email = models.EmailField(verbose_name=_("Email address"), blank=True, null=True, unique=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name=_("Belongs to"),
    )
    manager_flag = models.BooleanField(default=False, verbose_name=_("Manager Flag"))

    class Meta:
        db_table = "member"
        verbose_name = _("Member")
        verbose_name_plural = _("Members")

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name} ({self.user.username})"


class Prefecture(models.Model):
    """都道府県マスタ"""

    code = models.CharField(_("Prefecture Code"), max_length=2, unique=True)  # 都道府県コード
    name = models.CharField(_("Prefecture Name"), max_length=100)  # 都道府県名

    class Meta:  # type: ignore
        db_table = "prefecture"
        verbose_name = _("Prefecture")
        verbose_name_plural = _("Prefectures")
        ordering = ("code",)

    def __str__(self):
        return f"{self.name}"


class Municipality(models.Model):
    """市区町村マスタ"""

    code = models.CharField(_("Municipality Code"), max_length=5, unique=True)  # 市区町村コード
    name = models.CharField(_("Municipality Name"), max_length=100, blank=True, null=True)  # 市区町村名
    name_kana = models.CharField(_("Municipality Name Kana"), max_length=100, blank=True, null=True)  # 市区町村名
    prefecture = models.ForeignKey(Prefecture, verbose_name=_("Prefecture"), on_delete=models.DO_NOTHING, blank=True, null=True)  # 都道府県コード

    class Meta:  # type: ignore
        db_table = "municipality"
        verbose_name = _("Municipality")
        verbose_name_plural = _("Municipalities")
        ordering = ("code",)

    def __str__(self):
        return f"{self.name}({self.code})"


class Postcode(BaseModel):
    """郵便番号マスタ"""

    postcode = models.CharField(_("Postcode"), max_length=7, null=False, blank=False)  # 郵便番号
    municipality = models.ForeignKey(Municipality, verbose_name=_("Municipality"), on_delete=models.DO_NOTHING, blank=True, null=True)  # 市区町村
    town_name = models.CharField(_("Town Name"), max_length=1000, null=True, blank=True, default="")  # 町域名
    town_name_kana = models.CharField(_("Town Name Kana"), max_length=1000, null=True, blank=True, default="")  # 町域名カナ

    class Meta:  # type: ignore
        db_table = "postcode"
        verbose_name = _("Postcode")
        verbose_name_plural = _("Postcodes")
        ordering = ("postcode",)
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["postcode", "municipality", "town_name", "town_name_kana"],
                name="unique_postcode_postcode_town_name",
            )
        ]

    def __str__(self):
        return f"{self.postcode}"
