from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from apps.accounts.models import VerifyCode
from utils.utils import send_msg


@receiver(post_save, sender=VerifyCode)
def verify_post_save(sender, instance, created, **kwargs):
    if created:
        msg = render_to_string(
            'phone_verify.text',
            context={
                'verify_code': instance.verification_code,
            },
        )
        send_msg(instance.user.phone_number, msg)
