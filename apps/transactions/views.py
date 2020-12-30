import logging
from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.transactions.models import PurchasePackage

logger = logging.getLogger(__name__)


class PaymentView(View):
    def get(self, request, *args, **kwargs):
        transaction_id = request.GET.get('transaction_id')
        purchase_verified = request.GET.get('purchase_verified')

        if purchase_verified is None:
            return HttpResponse(
                'وضعیت سفارش نا معتبر می باشد! چنانچه از حساب شما مبلغی کسر شده است،'
                ' حداکثر تا ۷۲ ساعت آینده به حساب شما باز می گردد.'
            )
        purchase_verified = {'true': True}.get(purchase_verified.strip().lower(), False)

        with transaction.atomic():
            try:
                order = PurchasePackage.objects.select_related('package').select_for_update(of=('self',)).get(
                    transaction_id=transaction_id,
                    is_paid__isnull=True
                )
            except PurchasePackage.DoesNotExist:
                return HttpResponse('<h1>! سفارشی یافت نشد</h1>')
            now = timezone.now()
            user = order.user

            if purchase_verified:
                has_package = PurchasePackage.objects.filter(
                    expire_date__gt=now.date(),
                    user=user,
                    package=order.package,
                    is_paid=True
                ).order_by('-expire_date').first()

                if has_package:
                    start_date = has_package.expire_date
                    expire_date = start_date + order.package.duration
                else:
                    start_date = now.date()
                    expire_date = start_date + order.package.duration
                logger.info(
                    f"[Order payment done successfully]"
                    f"-[transaction_id: {transaction_id}]"
                    f"-[invoice-uuid: {str(order.invoice_uuid)}]"
                )
                order.start_date = start_date
                order.expire_date = expire_date
            else:
                logger.info(
                    f"[Order payment was unsuccessful]"
                    f"-[transaction_id: {transaction_id}]"
                    f"-[invoice-uuid: {str(order.invoice_uuid)}]"
                )
            order.is_paid = purchase_verified
            order.save()

        html = {
            True: 'transactions/payment_done.html',
            False: 'transactions/payment_failed.html'
        }.get(purchase_verified)

        # Making redirect url
        params = {'success': str(purchase_verified).lower()}
        url_parts = list(urlparse(order.redirect_url))
        query = dict(parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urlencode(query)
        redirect_url = urlunparse(url_parts)

        context = {
            "redirect_url": redirect_url,
            "purchase_verified": purchase_verified
        }
        return render(request, html, context)
