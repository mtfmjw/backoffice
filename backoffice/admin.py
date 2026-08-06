from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class CustomAdminSite(AdminSite):
    """Custom Admin Site that allows non-staff users to login"""

    site_title = _("バックオフィス")
    site_header = _("バックオフィス")
    index_title = _("サイト管理")

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
            if app['app_label'] == 'common':
                # 希望するモデルの順序（object_name：モデルのクラス名）をリストで指定
                ordering = ['Prefecture', 'Municipality', 'Postcode', 'Organization', 'Member']
                
                # 指定した順序に従って models リストを並び替え
                app['models'].sort(
                    key=lambda x: ordering.index(x['object_name']) if x['object_name'] in ordering else 999
                )
                
        return app_list


# Create an instance of the custom admin site to be used in urls.py
admin_site = CustomAdminSite()

from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin

admin_site.register(AuthUser, AuthUserAdmin)
admin_site.register(Group, GroupAdmin)
