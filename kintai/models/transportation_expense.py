from django.db import models

from common.models import Member
from common.models.base import ApprovedBaseModel
from common.models.transport import TransportationStation
from kintai.const import RouteType


class CommutingRoute(models.Model):
    """通勤経路"""

    station_from = models.ForeignKey(TransportationStation, on_delete=models.DO_NOTHING, related_name="+", verbose_name="出発駅")
    station_to = models.ForeignKey(TransportationStation, on_delete=models.DO_NOTHING, related_name="+", verbose_name="到着駅")
    transfer_station = models.CharField("経由駅", max_length=255, null=True, blank=True)
    route_type = models.IntegerField("経路種別", choices=RouteType.choices, null=True, blank=True)
    oneway_fare = models.IntegerField("片道運賃")

    class Meta:
        abstract = True


class CommutingRouteRegister(CommutingRoute, ApprovedBaseModel):
    """通勤経路登録"""

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, related_name="commuting_route_registers", verbose_name="社員")

    class Meta:
        db_table = "commuting_route_register"
        verbose_name = "通勤経路登録"
        verbose_name_plural = "通勤経路登録"
        unique_together = ("member",)


class MonthlyTransportationExpenseReport(CommutingRoute, ApprovedBaseModel):
    """交通費申請（1人1月あたりの確定データ）"""

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, related_name="monthly_transportation_expenses", verbose_name="組織メンバー")
    month = models.DateField("月")

    class Meta:
        db_table = "monthly_transportation_expense_report"
        verbose_name = "月次交通費申請"
        verbose_name_plural = "月次交通費申請"
        unique_together = ("member", "month")


class TransportationExpenseDetail(CommutingRoute):
    """交通費詳細"""

    monthly_report = models.ForeignKey(
        MonthlyTransportationExpenseReport, on_delete=models.CASCADE, related_name="details", verbose_name="交通費詳細"
    )
    day = models.DateField("日")
    is_registered_route = models.BooleanField("登録経路", default=False)
    is_round_trip = models.BooleanField("往復", default=False)
    visit_destination = models.CharField("訪問先", max_length=255, null=True, blank=True)
    visit_purpose = models.CharField("目的", max_length=255, null=True, blank=True)

    class Meta:
        db_table = "transportation_expense_detail"
        verbose_name = "交通費詳細"
        verbose_name_plural = "交通費詳細"
