from django.db import models

from common.const import ActiveStatus, LineType
from common.models.base import MemberScopedModel


class TransportationCompany(MemberScopedModel):
    """輸送事業者、駅データに準拠、https://ekidata.jp/"""

    class CompanyType(models.IntegerChoices):
        OTHER = 0, "その他"
        JR = 1, "JR"
        MAJOR = 2, "大手私鉄"
        MINOR = 3, "準大手私鉄"

    company_cd = models.IntegerField(unique=True, verbose_name="事業者コード")
    rr_cd = models.IntegerField(verbose_name="鉄道コード")  # 2桁整数
    company_name = models.CharField(max_length=80, verbose_name="事業者名")
    company_name_k = models.CharField(max_length=80, null=True, blank=True, verbose_name="事業者名カナ")
    company_name_h = models.CharField(max_length=80, null=True, blank=True, verbose_name="事業者名正式表記")
    company_name_r = models.CharField(max_length=80, null=True, blank=True, verbose_name="事業者名略称")
    company_url = models.URLField(max_length=255, null=True, blank=True, verbose_name="事業者URL")
    company_type = models.IntegerField(choices=CompanyType.choices, null=True, blank=True, verbose_name="事業者種別")
    e_status = models.IntegerField(choices=ActiveStatus.choices, null=True, blank=True, verbose_name="運用状況")

    class Meta:
        db_table = "transportation_company"
        verbose_name = "鉄道事業者"
        verbose_name_plural = "鉄道事業者"

    def __str__(self):
        return self.company_name


class TransportationLine(MemberScopedModel):
    """輸送事業者の路線"""

    # 整数5桁　鉄道コード + エリアコード + 連番　※新幹線は4桁
    line_cd = models.IntegerField(unique=True, verbose_name="路線コード")  # 整数5桁　鉄道コード + エリアコード + 連番　※新幹線は4桁
    company = models.ForeignKey(TransportationCompany, on_delete=models.CASCADE, related_name="lines", verbose_name="事業者")
    line_name = models.CharField(max_length=80, verbose_name="路線名")
    line_name_k = models.CharField(max_length=80, null=True, blank=True, verbose_name="路線名カナ")
    line_name_h = models.CharField(max_length=80, null=True, blank=True, verbose_name="路線名正式表記")
    line_type = models.IntegerField(choices=LineType.choices, null=True, blank=True, verbose_name="路線区分")
    e_status = models.IntegerField(choices=ActiveStatus.choices, null=True, blank=True, verbose_name="運用状況")

    class Meta:
        db_table = "transportation_line"
        verbose_name = "路線"
        verbose_name_plural = "路線"

    def __str__(self):
        return self.line_name


class TransportationStation(MemberScopedModel):
    """輸送事業者の駅"""

    station_cd = models.IntegerField(unique=True, verbose_name="駅コード")  # 整数7桁 ※新幹線は6桁
    station_g_cd = models.IntegerField(null=True, blank=True, verbose_name="駅グループコード")  # 整数6・7桁
    station_name = models.CharField(max_length=80, verbose_name="駅名")
    station_name_k = models.CharField(max_length=80, null=True, blank=True, verbose_name="駅名カナ")
    station_name_r = models.CharField(max_length=200, null=True, blank=True, verbose_name="駅名ローマ字")
    line = models.ForeignKey(TransportationLine, on_delete=models.CASCADE, related_name="stations", verbose_name="路線")
    address = models.CharField(max_length=300, null=True, blank=True, verbose_name="住所")
    lon = models.FloatField(null=True, blank=True, verbose_name="経度")
    lat = models.FloatField(null=True, blank=True, verbose_name="緯度")
    open_ymd = models.DateField(null=True, blank=True, verbose_name="開業日")
    close_ymd = models.DateField(null=True, blank=True, verbose_name="廃止日")
    e_status = models.IntegerField(choices=ActiveStatus.choices, null=True, blank=True, verbose_name="運用状況")

    class Meta:
        db_table = "transportation_station"
        verbose_name = "駅"
        verbose_name_plural = "駅"

    def __str__(self):
        return self.station_name
