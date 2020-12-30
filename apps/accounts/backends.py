from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import VerifyCode

User = get_user_model()
auth_user_settings = getattr(settings, 'AUTH_USER', {})


class SMSBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        PhoneNumberField = User._meta.get_field('phone_number')
        try:
            phone_number = int(kwargs.get('phone_number', 0))
            PhoneNumberField.run_validators(phone_number)
            verify_code = VerifyCode.objects.filter(
                user__phone_number=phone_number,
                verification_code=password,
                created_time__gt=timezone.now() - timezone.timedelta(hours=6),
                verify_time__isnull=True
            ).select_related('user').first()

            if verify_code:
                cache_value = cache.get(f'forget_password_{phone_number}_{password}')
                verify_code.verify_time = timezone.now()
                verify_code.save()
                user = verify_code.user

                if cache_value:
                    user.set_unusable_password()
                    user.save()
                    cache.delete(f'forget_password_{phone_number}_{password}')
                return user
        except (ValueError, ValidationError):
            pass
