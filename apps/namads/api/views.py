from django_filters.rest_framework import DjangoFilterBackend


from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.blog.api.serializers import NamadSerializer
from apps.commenting.api.serializers import BaseCommentVoteSerializer, BaseCommentSerializer
from apps.commenting.api.views import BaseCommentViewSet
from apps.namads.models import Namad, NamadComment, NamadCommentVote
from utils.permissions import FilterPermission
from utils.utils import redis_cache


class NamadViewSet(ListModelMixin,
                   RetrieveModelMixin,
                   GenericViewSet):
    """

        list:
            Return all namads, ordered by most recently added.

            query parameters
            -  Ordering fields: 'id'. Ex: ?ordering=id
            -  Search fields: 'name', 'namad_id', 'group_name' . Ex: ?search=some random name.
        retrieve:
            Return a specific namad detail.

        add_comment:
            Add a new comment to specific namad.

        chart_data:
            Return daily and sections data based on specific namad id

            Extra info: {
                'sections': {
                'money_entry_graph': {time, buy_per_i, sell_per_i, i_buyer_seller_pow}
                'order_status_table': {
                    zd1, qd1, pd1, po1, qo1, zo1,
                    zd2, qd2, pd2, po2, qo2, zo2,
                    zd13, qd3, pd3, po3, qo3, zo3,
                }
                }
                'daily': {
                    'price_volume_graph': { (stat_date, jalali_stat_date, pc, tvol), ...}
                }
            }
            Note: The keys that aren't mentioned have names.

        advance_data:
            Return advance filter data based on specific namad id
    """
    serializer_class = NamadSerializer
    queryset = Namad.objects.filter(is_enable=True).order_by('-id')
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'namad_id', 'group_name']
    ordering_fields = ['id', ]

    def get_serializer_class(self):
        # Note: this part is just for showing better documentation on swagger
        if self.action == 'add_comment':
            BaseCommentSerializer.Meta.model = NamadComment
            BaseCommentSerializer.Meta.fields = [
                'id', 'user_profile', 'content', 'namad',
                'positive_votes_sum', 'negative_votes_sum',
                'user_vote', 'created_time'
            ]
            BaseCommentSerializer.Meta.read_only_fields = ['id', 'namad', 'created_time', ]
            return BaseCommentSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=['post'], url_path='add-comment')
    def add_comment(self, request, *args, **kwargs):
        namad = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, namad=namad)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, url_path='chart-data')
    def chart_data(self, request, *args, **kwargs):
        namad = self.get_object()
        chart_data = redis_cache.get(namad.id, {})
        chart_data.pop('filter_data', None)
        return Response(chart_data)

    @action(detail=True, url_path='advance-data', permission_classes=[FilterPermission, ])
    def advance_data(self, request, *args, **kwargs):
        namad = self.get_object()
        filter_data = redis_cache.get(namad.id, {})
        return Response(filter_data)


class NamadCommentViewSet(BaseCommentViewSet):
    """

        list:
            Return all comments, ordered by most recently added.

            query parameters
            -  filter fields: 'namad'. Ex: ?namad=1.

        vote:
            Set a vote between -1 to 1 for a specific namad's comment.

    """
    model_class = NamadComment
    filter_fields = ('namad',)

    def get_serializer_class(self):
        # Note: this part is just for showing better documentation on swagger
        if self.action == 'vote':
            serializer = BaseCommentVoteSerializer
            serializer.Meta.model = NamadCommentVote
        else:
            serializer = super().get_serializer_class()
            serializer.Meta.fields = [
                'id', 'user_profile', 'namad', 'content',
                'positive_votes_sum', 'negative_votes_sum',
                'user_vote', 'created_time'
            ]
            serializer.Meta.read_only_fields = ['id', 'namad', 'created_time', ]
            serializer.Meta.model = NamadComment
        return serializer
