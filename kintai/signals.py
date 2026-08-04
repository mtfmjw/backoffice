from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from kintai.models import Member

User = get_user_model()


@receiver(post_save, sender=User)
def create_member_for_new_user(sender, instance, created, **kwargs):
    if created:
        Member.objects.get_or_create(user=instance, defaults={"email": instance.email})
    else:
        member = Member.objects.filter(user=instance).first()
        if member is None:
            Member.objects.get_or_create(user=instance, defaults={"email": instance.email})
        elif instance.email and member.email is None:
            member.email = instance.email
            member.save()
