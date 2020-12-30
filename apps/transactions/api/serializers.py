import logging

import requests

from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from apps.transactions.models import Package, PurchasePackage

logger = logging.getLogger(__name__)


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ['id', 'name', 'price', 'price_discount', 'duration', 'is_filter', 'is_article']


class PurchasePackageSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        remove_fields = kwargs.pop('remove_fields', None)
        super(PurchasePackageSerializer, self).__init__(*args, **kwargs)

        if remove_fields:
            # for multiple fields in a list
            for field_name in remove_fields:
                self.fields.pop(field_name, None)

    gateway = serializers.IntegerField(write_only=True)
    package = PackageSerializer(read_only=True)
    remaining_days = serializers.SerializerMethodField()

    class Meta:
        model = PurchasePackage
        fields = [
            'id', 'price', 'package', 'is_paid',
            'created_time', 'start_date', 'expire_date',
            'remaining_days', 'redirect_url', 'gateway'
        ]
        read_only_fields = ['id', 'price', 'is_paid', 'created_time', 'start_date', 'expire_date']
        extra_kwargs = {
            'redirect_url': {
                'write_only': True,
                'required': True
            },
        }

    def get_remaining_days(self, obj):
        today_date = timezone.now().date()

        if obj.expire_date and obj.expire_date > today_date:
            return (obj.expire_date - today_date).days
        return 0

    def create(self, validated_data):
        gateway = validated_data['gateway']
        purchase = validated_data['purchase']
        purchase_r = object

        try:
            data = {
                'gateway': gateway,
                'order': str(purchase.invoice_uuid)
            }
            headers = {
                "Authorization": f"TOKEN {settings.PAYMENT_SERVICE_SECRET}"
            }

            purchase_r = requests.post(
                headers=headers,
                url=f'{settings.PAYMENT_GATE_WAY_URL}/api/v1/payment/purchase/gateway/',
                json=data,
                timeout=(3, 6)
            )
            purchase_r.raise_for_status()
        except requests.HTTPError as e:
            logger.error(
                f"[HTTP exception occurred while ordering purchase]"
                f"-[response: {purchase_r.content}]"
                f"-[transaction_id: {purchase.transaction_id}]"
                f"-[invoice-uuid: {str(purchase.invoice_uuid)}]"
                f"-[error: {e}]"
            )
            raise serializers.ValidationError(_('error in getting order gateway'))
        except Exception as e:
            logger.error(
                f"[Bare exception occurred while ordering purchase]"
                f"-[transaction_id: {purchase.transaction_id}]"
                f"-[invoice-uuid: {str(purchase.invoice_uuid)}]"
                f"-[error: {e}]"
            )
            raise serializers.ValidationError(_('Bare exception occurred in getting order gateway'))

        logger.info(
            f"[order purchase done successfully]"
            f"-[response: {purchase_r.content}]"
            f"-[transaction_id: {purchase.transaction_id}]"
            f"-[invoice-uuid: {str(purchase.invoice_uuid)}]"
        )
        self.validated_data['gateway_url'] = purchase_r.json().get('gateway_url')
        return purchase

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = super().to_representation(instance)
        try:
            gateway_url = self.validated_data.get('gateway_url')
        except AssertionError:
            gateway_url = None
        if gateway_url:
            ret.update({'gateway_url': gateway_url})
        return ret
