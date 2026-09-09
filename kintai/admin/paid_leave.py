from datetime import date

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.shortcuts import redirect
from django.urls import path
from django.utils.timezone import localdate
from django.utils.translation import gettext as _

from backoffice.admin import admin_site
from common.admin.base import RowScopedBaseModelAdmin
from common.admin.filters import YearFilter
from common.models.member import Member
from kintai.models.paid_leave import PaidLeave


class PaidLeaveYearFilter(YearFilter):
    field_name = "valid_from"
    start_year = 2024


@admin.register(PaidLeave, site=admin_site)
class PaidLeaveAdmin(RowScopedBaseModelAdmin):
    change_list_template = "kintai/paidleave/change_list.html"
    list_filter = (PaidLeaveYearFilter,)
    list_display = ("member", "join_date", "valid_from", "valid_till", "acquired_days", "remaining_days")
    fields = (("member", "join_date"), ("valid_from", "valid_till"), ("acquired_days", "remaining_days"))

    def join_date(self, obj):
        return obj.member.join_date if obj.member else None

    join_date.short_description = _("Join Date")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        readonly_fields.extend(["member", "valid_from", "valid_till", "acquired_days", "join_date"])
        if obj and not request.user.member.is_accounting_staff:
            readonly_fields.append("remaining_days")
        return readonly_fields

    def has_import_permission(self, request, obj=None):
        return False

    def has_export_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # 初期表示時のフィルターパラメータ調整
        if not request.GET:
            q = request.GET.copy()
            q["year"] = "all"
            return redirect(f"{request.path}?{q.urlencode()}")

        extra_context = extra_context or {}
        grant_year = self.model.objects.order_by("-valid_from").values_list("valid_from__year", flat=True).first()
        if grant_year is None:
            grant_year = localdate().year if localdate().month < 10 else localdate().year + 1

        extra_context["grant_year"] = grant_year
        extra_context["grant_annual_leave_label"] = _("Grant annual leave(%(year)s) Oct.") % {"year": grant_year}
        return super().changelist_view(request, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        ungranted = Member.objects.filter(paid_leaves__isnull=True, valid_flag=True, join_date__isnull=False)

        if not ungranted:
            self.message_user(request, _("No members found without granted paid leave."), messages.WARNING)
            return redirect(self.redirect_to_changelist(request))

        paid_leave_id = 0
        for member in ungranted:
            acquired_days = 0
            with connection.cursor() as cursor:
                cursor.execute("SELECT get_paid_leave_days(%s)", (member.join_date,))
                acquired_days = cursor.fetchone()[0]
            obj = PaidLeave.objects.create(
                member=member,
                valid_from=member.join_date,
                valid_till=date(member.join_date.year + 2, 9, 30),
                acquired_days=acquired_days,
                remaining_days=acquired_days,
                created_by=request.user,
                updated_by=request.user,
            )
            if not paid_leave_id:
                paid_leave_id = obj.pk

        return redirect(self.redirect_to_change(request, paid_leave_id))

    def get_urls(self):
        urls = super().get_urls()
        app, model = self.opts.app_label, self.opts.model_name
        custom_urls = [
            path("grant-annual-leave/", self.admin_site.admin_view(self.grant_annual_leave), name=f"{app}_{model}_grant_annual_leave"),
        ]
        return custom_urls + urls

    def grant_annual_leave(self, request):
        if not request.user.is_authenticated or not hasattr(request.user, "member"):
            raise PermissionDenied

        redirect_to = self.redirect_to_changelist(request)

        grant_year = request.GET.get("grant_year", None)
        if grant_year is None:
            self.message_user(request, _("To grant annual leave, please specify the year."), messages.ERROR)
            return redirect(redirect_to)

        valid_from = date(int(grant_year), 10, 1)
        if self.model.objects.filter(valid_from=valid_from).exists():
            self.message_user(request, _("Annual leave for the specified year has already been granted."), messages.ERROR)
            return redirect(redirect_to)

        # Grant annual leave for the specified year
        with connection.cursor() as cursor:
            cursor.execute("CALL grant_annual_leave(%s, %s)", [grant_year, request.user.username])
        self.message_user(request, _("Annual leave for the specified year has been successfully granted."), messages.SUCCESS)
        return redirect(redirect_to)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        print("Unfiltered count:", self.model.objects.count())
        print("Scoped count:", qs.count())
        return qs
