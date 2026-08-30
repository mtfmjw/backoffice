from datetime import time

from django.db import models
from django.utils.translation import gettext_lazy as _

NIGHT_START_TIME = time(22, 0)
NIGHT_END_TIME = time(5, 0)
HALF_DAY_MINUTES = 180  # 半日休暇の時間（分）
TIME_UNIT = 15  # 勤怠計算の時間単位（分）、当該単位で切り捨てて計算する。15分単位で計算する場合は15、30分単位で計算する場合は30を設定する。

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


class ApproveStatus(models.IntegerChoices):
    DRAFT = 0, _("Draft")  # 入力中
    APPLIED = 1, _("Applied")  # 申請済
    APPROVED = 2, _("Approved")  # 承認済
    REJECTED = 3, _("Rejected")  # 却下
    CONFIRMED = 4, _("Confirmed")  # 確定済


class DateType(models.IntegerChoices):
    """勤務日分類"""

    WORK_DAY = 0, _("Work Day")  # 平日
    SCHEDULED_DAY_OFF = 1, _("Scheduled Day Off")  # 所定休日(週休2日制の土曜日、年末年始など)
    STATUTORY_DAY_OFF = 2, _("Statutory Day Off")  # 法定休日（法律で定められた月4回の休日、日曜日など）
    NATIONAL_HOLIDAY = 3, _("National Holiday")  # 国民の祝日
    TRANSFER_HOLIDAY = 4, _("Transfer Holiday")  # 振替休日、祝日が土日と重なった場合に、翌日を振替休日（法定休日）とする


class DateStatus(models.IntegerChoices):
    """就業区分"""

    PRESENT = 0, _("Present")  # 出勤
    ABSENCE = 1, _("Absence")  # 欠勤
    MORNING_PAID_LEAVE = 2, _("Morning Half-Day Leave")  # 午前半休
    AFTERNOON_PAID_LEAVE = 3, _("Afternoon Half-Day Leave")  # 午後半休
    PAID_LEAVE = 4, _("Paid Leave")  # 有給休暇
    # 特別休暇：結婚、忌引、出産、育児、介護などの理由で取得する休暇。会社の規定に基づき、特別な理由で取得する休暇であり、通常の有給休暇とは異なる。
    SPECIAL_PAID_LEAVE = 5, _("Special Paid Leave")  # 特別休暇
    # 振替休日：出勤する前に、あらかじめ休日と入れ替えた日。休日と労働日を交換したため、出勤日（元の休日）は通常の労働日となる。
    SUBSTITUTE_HOLIDAY = 6, _("Substitute Holiday")  # 振替休日
    # 代休日：休日に出勤して、後日休んだ日。休日に出勤したため、出勤日（元の休日）は休日出勤となる。
    COMPENSATORY_HOLIDAY = 7, _("Compensatory Holiday")  # 代休
    SP5 = 8, _("SP5")  # 4-5月：ゴールデンウイーク2日、7-9月：夏季休暇3日、12/29-1/3：年末年始休暇6日

    # 生理休暇
    MENSTRUAL_LEAVE = 100, "生理休暇"  # 生理休暇
    # 育児休暇
    CHILDCARE_LEAVE = 101, "子育て休暇"  # 子育て休暇
    # 介護休暇
    CARE_LEAVE = 102, "介護休暇"  # 介護休暇
    # 産前休暇
    PRENATAL_LEAVE = 103, "産前休暇"  # 産前休暇
    # 産後休暇
    POSTNATAL_LEAVE = 104, "産後休暇"  # 産後休暇
    # 育児休業
    CHILDCARE_LEAVE_OF_ABSENCE = 105, "育児休業"  # 育児休業
    # 再雇用RF休暇
    REEMPLOYMENT_RF_LEAVE = 106, "再雇用RF休暇"  # 再雇用RF休暇