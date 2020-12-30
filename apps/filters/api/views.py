import logging

from uuid import uuid4


from django.core.cache import cache
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.filters.api.serializers import FilterCategorySerializer
from apps.filters.models import SignalFilter, FilterCategory
from apps.transactions.models import PurchasePackage
from utils.permissions import FilterPermission


logger = logging.getLogger(__name__)
TICKET_EXPIRE_TIME = 2 * 60


class RegisterFilterAPIView(APIView):
    """
        get:
            API view for retrieving ticket uuid.
    """
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get(self, request, *args, **kwargs):
        ticket_uuid = str(uuid4())

        if request.user.is_anonymous:
            cache.set(ticket_uuid, False, TICKET_EXPIRE_TIME)
        else:
            has_package = PurchasePackage.objects.filter(
                user=request.user,
                is_paid=True,
                expire_date__gt=timezone.now().date(),
                package__is_filter=True
            ).exists()
            cache.set(ticket_uuid, has_package, TICKET_EXPIRE_TIME)

        return Response({'ticket_uuid': ticket_uuid})


class InitialFilterAPIView(APIView):
    """
    get:
        API view for retrieving initial signal data based on specific category id.

    """
    authentication_classes = (JWTAuthentication,)
    permission_classes = (FilterPermission,)

    def get(self, request, *args, **kwargs):
        data = []
        category = kwargs['category_id']

        all_filters = SignalFilter.objects.filter(
            is_enable=True,
            category=category
        ).values_list('filter_code', flat=True)
        cached_data = cache.get_many(all_filters)
        for _k, _v in cached_data.items():
            data.append({'filter_code': _k, 'data': _v})

        return Response(data=data)


class FilterCategoryView(ReadOnlyModelViewSet):
    """

        list:
            Return all categories, ordered by most recently added.

            query parameters
            -  filter fields: 'is_free'. Ex: ?is_free=1/0 or ?is_free=true/false

        retrieve:
            Return a specific category detail based on it's id.

    """
    serializer_class = FilterCategorySerializer
    queryset = FilterCategory.objects.filter(is_enable=True).prefetch_related('filters')
    filter_backends = [DjangoFilterBackend, ]
    filter_fields = ('is_free', )
