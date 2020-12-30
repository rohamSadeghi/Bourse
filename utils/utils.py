import logging

import requests

from django.core.cache import caches
from django.conf import settings
from django.contrib import admin
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from khayyam import JalaliDatetime

from rest_framework import serializers
from rest_framework.reverse import reverse as api_reverse

from apps.transactions.api.serializers import PurchasePackageSerializer
from apps.transactions.models import PurchasePackage

redis_cache = caches['redis']
logger = logging.getLogger('accounts')


class ApprovedListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('approved')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'approved'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('approved', _('approved')),
            ('not-approved', _('not approved')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # to decide how to filter the queryset.
        if self.value() == 'approved':
            queryset = queryset.exclude(approved_user__isnull=True)
            return queryset
        if self.value() == 'not-approved':
            queryset = queryset.filter(approved_user__isnull=True)
            return queryset


class ApprovedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(approved_time__isnull=False, approved_user__isnull=False, is_enable=True)


def article_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT /articles/<article's title-filename>
    return f"articles/{instance.title}-{filename}"


def filter_category_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT /filters/categories/<category's title-filename>
    return f"filters/categories/{timezone.now().microsecond}-{filename}"


def profile_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT /profiles/<profile's title-filename>
    return f"profiles/{instance.first_name}-{filename}"

maketrans = lambda A, B: dict((ord(a), b) for a, b in zip(A, B))
number_converter = maketrans(
    u'١٢٣٤٥٦٧٨٩٠۱۲۳۴۵۶۷۸۹۰٤٥٦₀₁₂₃₄₅₆₇₈₉¹²⁰⁴⁵⁶⁷⁸⁹①②③④⑤⑥⑦⑧⑨⑴⑵⑶⑷⑸⑹⑺⑻⑼⒈⒉⒊⒋⒌⒍⒎⒏⒐',
    u'123456789012345678904560123456789120456789123456789123456789123456789'
)


def send_msg(phone_number, message):
    data = {
        "data": [
            {
                "text": message,
                "phone_numbers": [phone_number]
            }
        ]
    }
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Token {settings.SMS_GATE_WAY_TOKEN}"
    }
    r = object

    try:
        r = requests.post(
            headers=headers,
            url=settings.SMS_GATE_WAY_URL,
            json=data,
            timeout=(3, 6)
        )
        r.raise_for_status()
    except requests.HTTPError as e:
        logger.error(
            f"[HTTP exception occurred while sending SMS]"
            f"-[func-name: {send_msg.__name__}]"
            f"-[response: {r.content}]"
            f"-[phone-number: {phone_number}]"
            f"-[error: {e}]"
            f"-[message: {message}]"
        )
        return False
    except Exception as e:
        logger.error(
            f"[Bare exception occurred while sending SMS]"
            f"-[func-name: {send_msg.__name__}]"
            f"-[phone-number: {phone_number}]"
            f"-[error: {e}]"
            f"-[message: {message}]"
        )
        return False
    logger.info(
        f"[SMS sent successfully]"
        f"-[func-name: {send_msg.__name__}]"
        f"-[response: {r.content}]"
        f"-[phone-number: {phone_number}]]"
        f"-[message: {message}]"
    )
    return True


def get_or_create_purchase(package, user):
    purchase = PurchasePackage.objects.filter(
        package=package,
        user=user,
        price=package.price - package.price_discount,
        is_paid__isnull=True
    ).first()

    if not purchase:
        purchase = PurchasePackage.objects.create(
            package=package,
            user=user,
            price=package.price - package.price_discount
        )
    if purchase.updated_time < timezone.now() - timezone.timedelta(days=6):
        # In order to set a new updated time, because in PurchasePackage API we will show
        # objects with 7 days updated time range
        purchase.save(update_fields=['updated_time'])
    return purchase


def order_payment(purchase, request):
    purchase_r = object
    serializer = PurchasePackageSerializer(data=request.data, remove_fields=['gateway', ])
    serializer.is_valid(raise_exception=True)
    r_url = serializer.validated_data['redirect_url']

    try:
        headers = {
            "Authorization": f"TOKEN {settings.PAYMENT_SERVICE_SECRET}"
        }
        data = {
            'is_paid': purchase.is_paid,
            "price": purchase.price,
            "service_reference": str(purchase.invoice_uuid),
            "properties":
                {
                    "redirect_url": api_reverse('payment-done', request=request)
                }
        }
        purchase_r = requests.post(
            headers=headers,
            url=f'{settings.PAYMENT_GATE_WAY_URL}/api/v1/payment/orders/',
            json=data,
            timeout=(3, 6)
        )
        purchase_r.raise_for_status()
    except requests.HTTPError as e:
        logger.error(
            f"[HTTP exception occurred while choosing gateway]"
            f"-[response: {purchase_r.content}]"
            f"-[invoice-uuid: {str(purchase.invoice_uuid)}]"
            f"-[error: {e}]"
        )
        raise serializers.ValidationError(_("Could not reach the payment url"))
    except Exception as e:
        logger.error(
            f"[Bare exception occurred while choosing gateway]"
            f"-[invoice-uuid: {str(purchase.invoice_uuid)}]"
            f"-[error: {e}]"
        )
        raise serializers.ValidationError(_("Bare exception occurred while trying to purchase"))

    response = purchase_r.json()
    purchase.transaction_id = response.get('transaction_id')
    purchase.redirect_url = r_url
    purchase.save()
    logger.info(
        f"[choose gateway done successfully]"
        f"-[response: {purchase_r.content}]"
        f"-[transaction_id: {purchase.transaction_id}]"
        f"-[invoice-uuid: {str(purchase.invoice_uuid)}]"
    )
    _r = {}
    _r.update({'gateways': response.get('gateways')})
    _r.update({'purchase': PurchasePackageSerializer(instance=purchase).data})
    return _r


class JalaliTimeMixin:
    @property
    def jalali_published_time(self):
        if self.approved_time:
            return JalaliDatetime(self.approved_time).strftime('%C')
        return ''


def update_namad_data(namad_id, key, data, clear=False):
    """
    This function will update namad's data in redis cache
    :param namad_id: id of specific namad
    :param key: key of namad's data dict which should be updated
    :param data: data of specific key in cached data
    :param clear: determine if sections data should be cleared
    :return:
    """
    appendable = {
        'sections': ['money_entry_graph'],
    }

    to_update_data = redis_cache.get(namad_id, {})
    sub_data = to_update_data.get(key, {})

    for k in appendable.get(key, []):
        if not clear:
            _d = sub_data.get(k, [])
            _d.append(data[k])
        else:
            _d = []
        data[k] = _d

    sub_data.update(data)
    to_update_data[key] = sub_data
    redis_cache.set(namad_id, to_update_data)
