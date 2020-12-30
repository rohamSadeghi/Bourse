from django.db.models import Q
from django_elasticsearch_dsl.search import Search

from django_elasticsearch_dsl_drf.constants import (
    LOOKUP_FILTER_TERMS,
    LOOKUP_FILTER_RANGE,
    LOOKUP_FILTER_PREFIX,
    LOOKUP_FILTER_WILDCARD,
    LOOKUP_QUERY_IN,
    LOOKUP_QUERY_GT,
    LOOKUP_QUERY_GTE,
    LOOKUP_QUERY_LT,
    LOOKUP_QUERY_LTE,
    LOOKUP_QUERY_EXCLUDE,
    SUGGESTER_COMPLETION,
    SUGGESTER_PHRASE,
    SUGGESTER_TERM
)
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    IdsFilterBackend,
    OrderingFilterBackend,
    DefaultOrderingFilterBackend,
    CompoundSearchFilterBackend,
)
from django_elasticsearch_dsl_drf.viewsets import SuggestMixin
from django_elasticsearch_dsl_drf.pagination import PageNumberPagination
from elasticsearch_dsl import connections
from hazm import Normalizer

from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse as api_reverse
from rest_framework.viewsets import GenericViewSet

from apps.blog.api.serializers import ArticleSerializer, NamadSerializer
from apps.blog.documents import ArticleDocument
from apps.blog.models import Article
from apps.namads.models import Namad
from apps.search_api.serializers import ArticleDocumentSerializer
from utils.filters import CustomSuggesterFilterBackend


class BaseDocumentViewSet(mixins.ListModelMixin,
                          GenericViewSet):
    """Base document ViewSet."""

    document_uid_field = 'id'
    document = None  # Re-define
    pagination_class = PageNumberPagination
    # permission_classes = (AllowAny,)
    ignore = []

    def __init__(self, *args, **kwargs):
        assert self.document is not None

        self.client = connections.get_connection(
            self.document._get_using()
        )
        self.index = self.document._index._name
        self.mapping = self.document._doc_type.mapping.properties.name
        self.search = Search(
            using=self.client,
            index=self.index,
            doc_type=self.document._doc_type.name
        )
        super(BaseDocumentViewSet, self).__init__(*args, **kwargs)

    def get_queryset(self):
        """Get queryset."""
        queryset = self.search.query()
        # Model- and object-permissions of the Django REST framework (
        # at the moment of writing they are ``DjangoModelPermissions``,
        # ``DjangoModelPermissionsOrAnonReadOnly`` and
        # ``DjangoObjectPermissions``) require ``model`` attribute to be
        # present in the queryset. Unfortunately we don't have that here.
        # The following approach seems to fix that (pretty well), since
        # model and object permissions would work out of the box (for the
        # correspondent Django model/object). Alternative ways to solve this
        # issue are: (a) set the ``_ignore_model_permissions`` to True on the
        # ``BaseDocumentViewSet`` or (b) provide alternative permission classes
        # that are almost identical to the above mentioned classes with
        # the only difference that they know how to extract the model from the
        # given queryset. If you think that chosen solution is incorrect,
        # please make an issue or submit a pull request explaining the
        # disadvantages (and ideally - propose  a better solution). Couple of
        # pros for current solution: (1) works out of the box, (2) does not
        # require modifications of current permissions (which would mean we
        # would have to keep up with permission changes of the DRF).
        queryset.model = self.document.Django.model
        return queryset


class ArticleSearchViewSet(BaseDocumentViewSet,
                           SuggestMixin):
    """

        list:
            Search on all articles, ordered by most recently added.

            query parameters
            -  Search fields: 'title', 'summary', 'tags.name', 'categories.title', 'namads.name',
                'namads.group_name' . Ex: ?search=some random name.
        suggest:
            Suggest categories and namad based on search parameters

            query parameters
                -  search param: Ex: ?search=search param
        retrieve:
            Return a specific article details.

    """
    serializer_class = ArticleDocumentSerializer
    document = ArticleDocument
    pagination_class = PageNumberPagination
    lookup_field = 'id'
    filter_backends = [
        FilteringFilterBackend,
        IdsFilterBackend,
        OrderingFilterBackend,
        DefaultOrderingFilterBackend,
        CompoundSearchFilterBackend,
        CustomSuggesterFilterBackend,
    ]
    search_fields = (
        'title',
        'summary',
        # 'tags.name',
        # 'categories.title',
        # 'namads.name',
        # 'namads.group_name'
    )
    filter_fields = {
        'id': {
            'field': 'id',
            # Note, that we limit the lookups of id field in this example,
            # to `range`, `in`, `gt`, `gte`, `lt` and `lte` filters.
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'namads': {
            'field': 'namads',
            # Note, that we limit the lookups of `pages` field in this
            # example, to `range`, `gt`, `gte`, `lt` and `lte` filters.
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },
        'title': "title.raw",
        'summary': 'summary',
        'categories': {
            'field': 'categories',
            # Note, that we limit the lookups of `pages` field in this
            # example, to `range`, `gt`, `gte`, `lt` and `lte` filters.
            'lookups': [
                LOOKUP_FILTER_RANGE,
                LOOKUP_QUERY_GT,
                LOOKUP_QUERY_GTE,
                LOOKUP_QUERY_LT,
                LOOKUP_QUERY_LTE,
            ],
        },

        'tags': {
            'field': 'tags',
            # Note, that we limit the lookups of `tags` field in
            # this example, to `terms, `prefix`, `wildcard`, `in` and
            # `exclude` filters.
            'lookups': [
                LOOKUP_FILTER_TERMS,
                LOOKUP_FILTER_PREFIX,
                LOOKUP_FILTER_WILDCARD,
                LOOKUP_QUERY_IN,
                LOOKUP_QUERY_EXCLUDE,
            ],
        },
    }
    # Suggester fields
    suggester_fields = {
        'title_suggest': {
            'field': 'title',
            'suggesters': [
                SUGGESTER_TERM,
                SUGGESTER_PHRASE,

            ],
            'options': {
                'size': 3,  # Number of suggestions to retrieve.
                'skip_duplicates': True,  # Whether duplicate suggestions should be filtered out.
            }
        },
        'title': {
            'field': 'title',
            'suggesters': [
                SUGGESTER_COMPLETION,
            ],
        },
        'summary_suggest': {
            'field': 'summary',
            'suggesters': [
                SUGGESTER_TERM,
                SUGGESTER_PHRASE,

            ],
        },
        'tags': {
            'field': 'tags.name.suggest',
            'suggesters': [
                SUGGESTER_COMPLETION,
            ],
        },
        'tags_suggest': {
            'field': 'tags.name',
            'suggesters': [
                SUGGESTER_TERM,
                SUGGESTER_PHRASE,
            ],
        },
        'categories_suggest': {
            'field': 'categories.title',
            'suggesters': [
                SUGGESTER_TERM,
                SUGGESTER_PHRASE,
            ],
        },
        'categories': {
            'field': 'categories.title.suggest',
            'suggesters': [
                SUGGESTER_COMPLETION,
            ],
        },
    }
    ordering_fields = {
        'id': 'id',
        'title': 'title',
        'summary': 'summary',
    }
    # Specify default ordering
    ordering = ('-id', )

    def list(self, request, *args, **kwargs):
        context = self.get_serializer_context()
        queryset = self.filter_queryset(self.get_queryset())
        search_param = request.query_params.get('search')

        if not search_param:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
        normalizer = Normalizer()
        search_param = normalizer.normalize(search_param)
        ready_data = []

        try:
            namad = Namad.objects.get(
                name=search_param,
                is_enable=True
            )
            namads_list = NamadSerializer([namad], many=True, context=context).data
        except Namad.DoesNotExist:
            namads = Namad.objects.filter(
                Q(name__istartswith=search_param) | Q(title__search=search_param),
                is_enable=True
            ).order_by('-id')
            namads_list = NamadSerializer(namads[:3], many=True, context=context).data

        all_categories = []
        all_slugs = {}
        serializer = self.get_serializer(queryset[:15], many=True)
        all_data = serializer.data
        for _d in all_data:
            for _c in _d['categories']:
                all_categories.append([_c['id'], _c['title']])
                all_slugs[_c['id']] = _c['slug']

        # Removing duplicates and sorting
        all_categories = set(tuple(_c) for _c in all_categories)
        all_categories = sorted(list(all_categories)[:3], reverse=True)
        for _c in all_categories:
            articles = Article.objects.filter(
                Q(title__search=search_param) | Q(summary__search=search_param),
                is_enable=True,
                categories=_c[0],

            ).order_by('-id')
            articles_data = ArticleSerializer(
                    articles[:3],
                    many=True,
                    context=context,
                    remove_fields=['namads']
                ).data
            if articles_data:
                ready_data.append({
                    "category": {"id": _c[0], "title": _c[1], "slug": all_slugs[_c[0]]},
                    "articles": articles_data
                })

        if not ready_data:
            ready_data = [
                {
                    'category': None,
                    'articles': [],
                }
            ]
        ready_data.append({'namads': namads_list})

        return Response(ready_data)

    @action(detail=False)
    def suggest(self, request):
        convert_result = []
        self.action = 'list'
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset[:15], many=True)
        all_data = serializer.data
        for d in all_data:
            convert_result.append(d['categories'])
        self.action = 'suggest'
        queryset = self.filter_queryset(self.get_queryset())
        is_suggest = getattr(queryset, '_suggest', False)
        namads_list = []
        search_param = request.query_params.get('search')

        if not is_suggest:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        if search_param:
            normalizer = Normalizer()
            search_param = normalizer.normalize(search_param)
            context = self.get_serializer_context()
            namads = Namad.objects.filter(
                Q(name__istartswith=search_param) | Q(title__search=search_param),
                is_enable=True
            ).order_by('-id')
            namads_list = NamadSerializer(namads[:3], many=True, context=context).data

        page = self.paginate_queryset(queryset)
        categories_result = page.get('article_title__completion')

        if categories_result is not None:
            to_replace_result = []
            for _c in categories_result:
                for _o in _c['options']:
                    convert_result.append(_o['_source']['categories'])
            page.pop('article_title__completion')
            for categories in convert_result:
                for category in categories:
                    query_params = f"?categories={category['id']}&search={search_param or ''}"
                    to_replace_result.append(category)
                    to_replace_result[-1].update(
                        {
                            'redirect_url': f"{api_reverse('articles-list', request=request)}{query_params}",
                            'query_params': query_params
                        }
                    )
            # Remove duplicate and sort results
            to_replace_result = [dict(t) for t in {tuple(d.items()) for d in to_replace_result}]
            to_replace_result = sorted(to_replace_result, key=lambda k: k['id'], reverse=True)
            page['categories'] = to_replace_result[:5]

        else:
            page['categories'] = []
        page['namads'] = namads_list
        return Response(page)
