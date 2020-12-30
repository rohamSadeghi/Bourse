from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.commenting.api.serializers import BaseCommentSerializer


class BaseCommentViewSet(ListModelMixin,
                         GenericViewSet):
    """

        list:
            Return all comments, ordered by most recently added.

            query parameters
            -  filter fields: 'article'. Ex: ?article=1.

        vote:
            Set a vote between -1 to 1 for a specific article.

    """
    serializer_class = BaseCommentSerializer
    model_class = None
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = [DjangoFilterBackend, ]

    def get_queryset(self):
        return self.model_class.approves.annotate(
            votes_sum=Coalesce(Sum('votes__vote'), 0),
            total_votes=Count('votes')
        ).select_related('user__profile').order_by('-votes_sum', '-total_votes')

    @action(detail=True, methods=['post'])
    def vote(self, request, *args, **kwargs):
        comment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, comment=comment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
