from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from utils.custom_fields import CustomBigIntegerField
from utils.utils import profile_directory_path
from utils.validators import clean_mobile_number_validator


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone_number, password, **extra_fields):
        """
        Create and save a user with the given phone number, and password.
        """
        if not phone_number:
            raise ValueError('The given phone number must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    phone_number = CustomBigIntegerField(_("phone number"), unique=True, validators=[clean_mobile_number_validator,])
    first_name = models.CharField(_("first name"), blank=True, max_length=50)
    last_name = models.CharField(_("last name"), blank=True, max_length=50)
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_('Designates whether the user can log into this admin site.'))
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def check_verify_code(self, verify_code):
        return self.verification_codes.filter(
            verification_code=verify_code,
            created_time__gt=timezone.now() - timezone.timedelta(hours=6),
            verify_time__isnull=True
        ).first()

    def set_verify_code(self, verify_code):
        self.verification_codes.create(verification_code=verify_code)

    def remove_verify_code(self, verify_code):
        self.verification_codes.filter(verification_code=verify_code).delete()

    def __str__(self):
        return f'{self.first_name}-{self.last_name}, {str(self.phone_number)}'


class UserProfile(models.Model):
    user = models.OneToOneField('User', verbose_name=_('user'), on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(_('first name'), max_length=50, blank=True)
    last_name = models.CharField(_('last name'), max_length=50, blank=True)
    avatar = models.ImageField(_('avatar'), blank=True, upload_to=profile_directory_path)
    gender = models.BooleanField(_('gender'), null=True, help_text=_('female is False, male is True, null is unset'))
    birth_date = models.DateField(_('birth date'), blank=True, null=True)
    email_address = models.EmailField(_('email address'), blank=True)

    class Meta:
        verbose_name = _('User profile')
        verbose_name_plural = _('User profiles')

    def __str__(self):
        return self.first_name or f"user id: {self.user_id}"

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class VerifyCode(models.Model):
    created_time = models.DateTimeField(_('creation time'), auto_now_add=True)
    user = models.ForeignKey(User, verbose_name=_('user'), related_name='verification_codes', on_delete=models.PROTECT)
    verification_code = models.PositiveIntegerField(_('verification code'))
    verify_time = models.DateTimeField(_('verification time'), null=True)

    class Meta:
        verbose_name = _('Verify code')
        verbose_name_plural = _('Verify codes')
        indexes = [
            models.Index(fields=['user', 'verification_code'], name='index_user_verification_code'),
        ]
