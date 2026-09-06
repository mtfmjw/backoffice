from django.db import models
from django.utils.translation import gettext_lazy as _

# 会社経営層グループ
COMPANY_EXECUTIVE_GROUP = "経営管理グループ"

# 組織責任者グループ
ORGANIZATION_MANAGER_GROUP = "組織責任者グループ"

# superuserの代わりに権限を明示的に付与してシステム管理を行うグループ
SYSTEM_INFO_GROUP = "情シスグループ"

# 勤怠管理グループ
ATTENDANCE_MANAGEMENT_GROUP = "勤怠管理グループ"

# 営業グループ
SALES_GROUP = "営業グループ"


class ApproveStatus(models.IntegerChoices):
    DRAFT = 0, _("Draft")  # 入力中
    APPLIED = 1, _("Applied")  # 申請済
    APPROVED = 2, _("Approved")  # 承認済
    REJECTED = 3, _("Rejected")  # 却下
    CONFIRMED = 4, _("Confirmed")  # 確定済


class ActiveStatus(models.IntegerChoices):
    ACTIVE = 0, "運用中"
    PRE_ACTIVE = 1, "運用前"
    INACTIVE = 2, "廃止"


class LineType(models.IntegerChoices):
    OTHER = 0, "その他"
    SHINKANSEN = 1, "新幹線"
    GENERAL = 2, "一般"
    SUBWAY = 3, "地下鉄"
    TRAM = 4, "市電・路面電車"
    MONORAIL = 5, "モノレール・新交通"
