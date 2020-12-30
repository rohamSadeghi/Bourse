from django.db.models import F
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.blog.api.serializers import (
    CategorySerializer,
    ArticleSerializer,
    BookmarkSerializer,
    RatingSerializer,
)
from apps.blog.models import Category, Article, ArticleComment, ArticleCommentVote, ArticleBookmark
from apps.commenting.api.serializers import BaseCommentVoteSerializer, BaseCommentSerializer
from apps.commenting.api.views import BaseCommentViewSet
from utils.filters import BaseRateOrdering, ArticleFilterBackend


class CategoryViewSet(ListModelMixin,
                      RetrieveModelMixin,
                      GenericViewSet):
    """

        list:
            Return all categories, ordered by most recently added.

            query parameters
            -  Ordering fields: 'id', 'title'. Ex: ?ordering=id
            -  Search fields: 'title' . Ex: ?search=some random name.
        retrieve:
            Return a specific category detail based on it's id.

    """
    serializer_class = CategorySerializer
    queryset = Category.parents.filter(is_enable=True)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['title', ]
    ordering_fields = ['id', 'title']

    def get_queryset(self):
        if self.action == 'retrieve':
            return Category.objects.filter(is_enable=True)
        return super().get_queryset()


class ArticleViewSet(ListModelMixin,
                     RetrieveModelMixin,
                     GenericViewSet):
    """

        list:
            Return all articles, ordered by most recently added.

            query parameters
            -  Ordering fields: 'id', 'rating_count', 'views_count',
                'approved_time' and 'rating_avg'. Ex: ?ordering=id
            -  Search fields: 'title' . Ex: ?search=some random name.
            -  filter fields: 'categories', 'namads', 'tags__name', 'brand', ''categories__slug'' and 'is_free'.
             Ex: ?categories=1 or ?is_free=true/false or ?tags__name=first tag
        retrieve:
            Return a specific article detail.
        bookmark:
            Set an article as an user favorite item.
        bookmarks_list:
            Return all user's bookmarked articles.
        rate:
            Set a rate between 1 to 5 for a specific article.
        add_comment:
            Add a new comment to specific article.
    """
    serializer_class = ArticleSerializer
    queryset = Article.approves.order_by('-approved_time')
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    filter_backends = [ArticleFilterBackend, filters.SearchFilter, BaseRateOrdering]
    filter_fields = ('categories', 'categories__slug', 'namads', 'is_free', 'tags__name')
    search_fields = ['title', '@title', '@summary']
    ordering_fields = ['id', 'approved_time', 'rating_count', 'rating_avg', 'views_count']
    
    def get_serializer_class(self):
        # Note: this part is just for showing better documentation on swagger
        actions_serializer_map = {
            'rate': RatingSerializer,
            'bookmark': BookmarkSerializer,
            'bookmarks_list': BookmarkSerializer,
            'add_comment': BaseCommentSerializer
        }
        BaseCommentSerializer.Meta.model = ArticleComment
        BaseCommentSerializer.Meta.fields = [
            'id', 'user_profile', 'content', 'article',
            'positive_votes_sum', 'negative_votes_sum',
            'user_vote', 'created_time'
        ]
        BaseCommentSerializer.Meta.read_only_fields = ['id', 'article', 'created_time', 'user_profile', ]
        return actions_serializer_map.get(self.action, super().get_serializer_class())

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Article.objects.filter(id=instance.id).update(views_count=F('views_count') + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def bookmark(self, request, *args, **kwargs):
        article = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, article=article)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, url_path='bookmarks-list')
    def bookmarks_list(self, request, *args, **kwargs):
        user = request.user
        if user and user.is_authenticated:
            return Response(
                self.get_serializer(
                ArticleBookmark.objects.filter(user=user, status=True),
                many=True
                ).data
            )
        return Response([])

    @action(detail=True, methods=['post'])
    def rate(self, request, *args, **kwargs):
        article = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, article=article)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='add-comment')
    def add_comment(self, request, *args, **kwargs):
        article = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, article=article)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ArticleCommentViewSet(BaseCommentViewSet):
    """

        list:
            Return all comments, ordered by most recently added.

            query parameters
            -  filter fields: 'article'. Ex: ?article=1.

        vote:
            Set a vote between -1 to 1 for a specific article's comment.

    """
    model_class = ArticleComment
    filter_fields = ('article',)

    def get_serializer_class(self):
        # Note: this part is just for showing better documentation on swagger
        if self.action == 'vote':
            serializer = BaseCommentVoteSerializer
            serializer.Meta.model = ArticleCommentVote
        else:
            serializer = super().get_serializer_class()
            serializer.Meta.fields = [
                'id', 'user_profile', 'article', 'content',
                'positive_votes_sum', 'negative_votes_sum',
                'user_vote', 'created_time'
            ]
            serializer.Meta.read_only_fields = ['id', 'article', 'created_time', 'user_profile', ]
            serializer.Meta.model = ArticleComment
        return serializer
