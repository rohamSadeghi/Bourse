import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

class Package(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    name = models.CharField(_('name'), max_length=50)
    duration = models.DurationField(_('duration'), help_text=_('Add duration in seconds or digits with white space for days. Ex: 30 0 for 30 days duration'))
    sku = models.CharField(_('SKU'), max_length=50, db_index=True, blank=True)
    price = models.PositiveIntegerField(_('price'))
    price_discount = models.PositiveIntegerField(_('price discount'), default=0)
    is_filter = models.BooleanField(_('is filter type'))
    is_article = models.BooleanField(_('is article type'))
    is_enable = models.BooleanField(_('is enable'), default=True)

    class Meta:
        verbose_name_plural = _("Packages")
        verbose_name = _("Package")

    def __str__(self):
        return self.name


class PurchasePackage(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), on_delete=models.CASCADE, related_name='purchases')
    package = models.ForeignKey('Package', verbose_name=_('package'), on_delete=models.CASCADE, related_name='purchases')
    invoice_uuid = models.UUIDField(_('invoice uuid'), default=uuid.uuid4, unique=True)
    transaction_id = models.CharField(_('transaction id'), max_length=40, null=True, unique=True)
    redirect_url = models.CharField(_('redirect url'), blank=True, max_length=150)
    price = models.PositiveIntegerField(_('price'), default=0)
    is_paid = models.BooleanField(_('is paid'), null=True)
    start_date = models.DateField(_('start date'), blank=True, null=True)
    expire_date = models.DateField(_('expire date'), blank=True, null=True)

    class Meta:
        verbose_name_plural = _("Purchase packages")
        verbose_name = _("Purchase package")

    def __str__(self):
        return f'user_id: {self.user_id} -> package_id: {self.package_id}'
