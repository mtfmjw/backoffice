from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class CustomAdminSite(AdminSite):
    """Custom Admin Site that allows non-staff users to login"""

    site_title = _("バックオフィス")
    site_header = _("バックオフィス")
    index_title = _("サイト管理")
    login_template = "registration/login.html"

    def has_permission(self, request):
        """
        Check if the user has permission to access the admin site.
        Allows any authenticated user, not just staff.
        """
        return request.user.is_authenticated

    def login(self, request, extra_context=None):
        """
        Overrides the default admin login view to allow any active user.
        """
        # If the user is already authenticated, redirect them to the admin index.
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy("admin:index"))

        extra_context = extra_context or {}
        extra_context["title"] = "Login"

        # If they are not authenticated, display the login form.
        # We are essentially using the standard LoginView, but within our custom admin site.
        return LoginView.as_view(
            template_name=self.login_template,
            extra_context={
                **self.each_context(request),
                **(extra_context or {}),
            },
        )(request)

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)

        # 対象のアプリ（common）を探して並び替える
        for app in app_list:
            if app["app_label"] == "common":
                # 希望するモデルの順序（object_name：モデルのクラス名）をリストで指定
                ordering = ["Prefecture", "Municipality", "Postcode", "Holiday", "WorkPattern", "Organization", "Member"]

                # 指定した順序に従って models リストを並び替え
                app["models"].sort(key=lambda x: ordering.index(x["object_name"]) if x["object_name"] in ordering else 999)
            elif app["app_label"] == "kintai":
                # 希望するモデルの順序（object_name：モデルのクラス名）をリストで指定
                ordering = ["MonthlyAttendance", "DailyAttendance"]

                # 指定した順序に従って models リストを並び替え
                app["models"].sort(key=lambda x: ordering.index(x["object_name"]) if x["object_name"] in ordering else 999)

        return app_list


# admin.py
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export import fields, resources
from import_export.admin import ImportExportMixin
from import_export.formats.base_formats import CSV
from import_export.widgets import ManyToManyWidget

User = get_user_model()

# superuserを一つに限定し、ほかのsuperuserを登録できないように制限する
SUPER_USER_NAME = "admin"

# 既存の UserAdmin の登録を解除（すでに登録されている場合）
admin.site.unregister(User)


class UserResource(resources.ModelResource):
    # Map M2M groups field cleanly if needed
    groups = fields.Field(attribute="groups", widget=ManyToManyWidget(Group, field="name"))

    class Meta:
        skip_unchanged = True
        report_skipped = True
        model = User
        # Exclude sensitive fields like password hash from export/import
        exclude = ("password", "user_permissions")
        # Specify explicit fields to control order
        fields = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "groups")
        import_id_fields = ("username",)


class GroupResource(resources.ModelResource):
    class Meta:
        model = Group
        fields = ("name",)
        import_id_fields = ("name",)
        skip_unchanged = True
        report_skipped = True


class CustomUserAdmin(ImportExportMixin, BaseUserAdmin):
    resource_class = UserResource
    formats = (CSV,)
    list_display = ("username", "email", "last_name", "first_name", "is_active")

    def get_form(self, request, obj=None, **kwargs):
        """
        フォームを生成する際、ログインユーザーが superuser でない場合は
        is_superuser フィールドを無効化（非表示・編集不可）にする
        """
        form = super().get_form(request, obj, **kwargs)

        # フィールドを無効化（HTML上で操作不可にする）
        if "is_superuser" in form.base_fields:
            form.base_fields["is_superuser"].disabled = True
            form.base_fields["is_superuser"].help_text = "スーパーユーザー権限の変更はできません。"

        return form

    def get_fieldsets(self, request, obj=None):
        """
        管理画面のフォーム表示領域から is_staff を除外する
        """
        fieldsets = super().get_fieldsets(request, obj)

        # fieldsets をディープコピーして非スーパーユーザー用に書き換え
        new_fieldsets = []
        for name, field_options in fieldsets:
            fields = list(field_options.get("fields", []))
            # is_staff をリストから削除
            if "is_staff" in fields:
                fields.remove("is_staff")
            new_fieldsets.append((name, {**field_options, "fields": tuple(fields)}))
        return tuple(new_fieldsets)

    def save_model(self, request, obj, form, change):
        """
        不正なリクエスト（POSTデータの改ざん等）を防止するため、
        保存時にも非スーパーユーザーによる is_superuser の昇格を弾く
        """
        if change:
            if obj.username == SUPER_USER_NAME:
                obj.is_superuser = True
            else:
                obj.is_superuser = False
        else:
            # 新規作成時は強制的に False に設定
            obj.is_superuser = False

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """
        superuser を閲覧できないようにする
        """
        qs = super().get_queryset(request)
        return qs.exclude(is_superuser=True)


class CustomGroupAdmin(ImportExportMixin, BaseGroupAdmin):
    resource_class = GroupResource
    formats = (CSV,)


# Create an instance of the custom admin site to be used in urls.py
admin_site = CustomAdminSite()


admin_site.register(User, CustomUserAdmin)
admin_site.register(Group, CustomGroupAdmin)

# 手動で保持したいメッセージをここに列挙する
_("Delete?")
