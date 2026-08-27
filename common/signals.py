from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.middleware import get_current_user
from common.models import Member

User = get_user_model()


@receiver(post_save, sender=User)
def create_member_for_new_user(sender, instance, created, **kwargs):

    if instance.username == "admin":
        return

    if created:
        Member.objects.get_or_create(
            user=instance, defaults={"email": instance.email, "created_by": get_current_user(), "updated_by": get_current_user()}
        )
    else:
        member = Member.objects.filter(user=instance).first()
        if member is None:
            current_user = get_current_user()
            if not current_user.is_authenticated:
                current_user = instance
            from .const import SYSTEM_INFO_GROUP

            if current_user.is_superuser or current_user.groups.filter(name=SYSTEM_INFO_GROUP).exists():
                # 情シスユーザーが初期ログインした時、Memberが存在しなければ新規作成する
                Member.objects.get_or_create(
                    user=instance, defaults={"email": instance.email, "created_by": current_user.username, "updated_by": current_user.username}
                )
        elif instance.email and (member.email is None or instance.email != member.email):
            member.email = instance.email
            member.updated_by = get_current_user()
            member.save()
