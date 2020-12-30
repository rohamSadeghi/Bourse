import logging

from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.accounts.api.serializers import UserRegistrationSerializer
from apps.accounts.models import User
from apps.transactions.api.serializers import PackageSerializer, PurchasePackageSerializer
from apps.transactions.models import Package, PurchasePackage
from utils.filters import PurchaseFilterBackend
from utils.utils import get_or_create_purchase, order_payment

logger = logging.getLogger(__name__)


class PackageViewSet(ListModelMixin,
                     RetrieveModelMixin,
                     GenericViewSet):
    """

        list:
            Return all packages, ordered by most recently added.

            query parameters
            -  filter fields: 'is_filter' and 'is_article'.
             Ex: ?is_filter=false/true.

        retrieve:
            Return a specific package detail.
        order_package:
            Order specific package based on it's pk for authenticated users.

            data
            -  {"redirect_url": "string"}
        anonymous_order_package:
            Order specific package based on it's pk for anonymous users.

            data
            -  {"phone_number": "string", "redirect_url": "string"}
    """
    serializer_class = PackageSerializer
    queryset = Package.objects.filter(is_enable=True).order_by('-id')
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None
    filter_backends = [DjangoFilterBackend, ]
    filter_fields = ['is_filter', 'is_article']

    def get_serializer_class(self):
        if self.action == 'order_package':
            return PurchasePackageSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=['post'], url_path='order-package')
    def order_package(self, request, *args, **kwargs):
        package = self.get_object()
        purchase = get_or_create_purchase(package, request.user)
        response = order_payment(purchase, request)
        return Response(response, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='anonymous-order-package', permission_classes=[])
    def anonymous_order_package(self, request, *args, **kwargs):
        package = self.get_object()
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            user = User.objects.create_user(
                phone_number=phone_number
            )
        purchase = get_or_create_purchase(package, user)
        response = order_payment(purchase, request)
        return Response(response, status=status.HTTP_201_CREATED)


class PurchasePackageViewSet(ListModelMixin,
                             RetrieveModelMixin,
                             GenericViewSet):
    """

        list:
            Return all package purchases of specific user, ordered by most recently added.

            query parameters
            -  filter fields: 'is_paid' and 'is_expired'.
             Ex: ?is_paid=none/true -> none: without payment and true for successful payments.
             Ex: ?is_expired=false/true -> false: non expired purchases and true for expired purchases.
        retrieve:
            Return a specific purchase package detail.
        purchase_order:
            Purchase an order based on specific gateway id.

            data
            -  {"gateway": "integer"}
        choose_gateway:
            Returns all available gateways to purchase an order.

    """
    serializer_class = PurchasePackageSerializer
    queryset = PurchasePackage.objects.filter(
        Q(is_paid=True) |
        Q(is_paid__isnull=True, updated_time__gt=timezone.now() - timezone.timedelta(days=7))
    ).order_by('-id')
    # Note: Do not change this query (from updated time to created time)
    # For more information check order_package action on Packages API
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated, )
    filter_backends = [PurchaseFilterBackend, ]
    filter_fields = ['is_paid', ]

    def get_queryset(self):
        if self.action == 'purchase_order':
            return super().get_queryset()
        return super().get_queryset().filter(user=self.request.user)

    @action(detail=True, url_path='choose-gateway')
    def choose_gateway(self, request, *args, **kwargs):
        response = order_payment(self.get_object(), request)
        return Response(response, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='purchase-order', permission_classes=[])
    def purchase_order(self, request, *args, **kwargs):
        purchase = self.get_object()
        serializer = self.get_serializer(data=request.data, remove_fields=['redirect_url',])
        serializer.is_valid(raise_exception=True)
        serializer.save(purchase=purchase)
        return Response(serializer.data)
