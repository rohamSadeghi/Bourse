from django.db.models import Avg, Count, Sum, Q
from django.db.models.functions import Coalesce
from django.http import QueryDict
from django.utils import timezone
from django_elasticsearch_dsl_drf.constants import SUGGESTER_TERM, SUGGESTER_PHRASE, SUGGESTER_COMPLETION
from django_elasticsearch_dsl_drf.filter_backends import SuggesterFilterBackend
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.filters import OrderingFilter

from apps.blog.models import Category


class BaseRateOrdering(OrderingFilter):

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            if any('rating_avg' in o for o in ordering):
                queryset = queryset.annotate(rating_avg=Coalesce(Avg('rates__rate'), 0))
            if any('rating_count' in o for o in ordering):
                queryset = queryset.annotate(rating_count=Count('rates'))
            if any('views_count' in o for o in ordering):
                queryset = queryset.annotate(Count('views_count'))
            queryset = queryset.order_by(*ordering)

        return queryset


class VoteOrdering(OrderingFilter):

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            if any('votes_sum' in o for o in ordering):
                queryset = queryset.annotate(votes_sum=Coalesce(Sum('votes__vote'), 0))
            if any('total_votes' in o for o in ordering):
                queryset = queryset.annotate(total_votes=Count('votes'))
            queryset = queryset.order_by(*ordering)
        return queryset


class ArticleFilterBackend(DjangoFilterBackend):
    def get_filterset_kwargs(self, request, queryset, view):
        # In order to filter children categories we used the following customization
        query_params_dict = request.query_params.copy()
        categories = query_params_dict.pop('categories', None)
        categories_slug = query_params_dict.pop('categories__slug', None)
        query_params = None

        if categories:
            try:
                if isinstance(categories, list):
                    categories = categories[0]
                categories = int(categories)
                categories_ids = Category.objects.get(id=categories).children.values_list('id', flat=True)
            except (Category.DoesNotExist, ValueError, TypeError):
                pass
            else:
                extended_categories = [categories]
                query_params = QueryDict(mutable=True)
                query_params.update(query_params_dict)
                extended_categories.extend(categories_ids)
                queryset = queryset.filter(categories__in=extended_categories)
                query_params._mutable = False

        if categories_slug:
            try:
                if isinstance(categories_slug, list):
                    categories_slug = categories_slug[0]
                categories_ids = Category.objects.get(slug=categories_slug).children.values_list('id', flat=True)
            except (Category.DoesNotExist, ValueError, TypeError):
                pass
            else:
                query_params = QueryDict(mutable=True)
                query_params.update(query_params_dict)
                queryset = queryset.filter(
                    Q(categories__slug=categories_slug) |
                    Q(categories__in=list(categories_ids))
                )
                query_params._mutable = False

        return {
            'data': query_params if query_params is not None else request.query_params,
            'queryset': queryset,
            'request': request,
        }


class PurchaseFilterBackend(DjangoFilterBackend):
    def get_filterset_kwargs(self, request, queryset, view):
        # In order to filter purchases based on expired ones we customize default filter
        is_expired = request.query_params.get('is_expired')
        is_paid = request.query_params.get('is_paid')

        if is_expired:
            if isinstance(is_expired, list):
                is_expired = is_expired[0]
            now = timezone.now().date()
            is_expired = {
                'true': {'expire_date__lt': now},
                'false': {'expire_date__gt': now}
            }.get(is_expired.strip().lower(), {})
            queryset = queryset.filter(**is_expired)

        if is_paid:
            if isinstance(is_paid, list):
                is_paid = is_paid[0]
            if is_paid.strip().lower() == 'none':
                queryset = queryset.filter(is_paid__isnull=True)

        return {
            'data': request.query_params,
            'queryset': queryset,
            'request': request,
        }


# Elastic suggester filter backend
class CustomSuggesterFilterBackend(SuggesterFilterBackend):
    @classmethod
    def apply_suggester_phrase(cls, suggester_name, queryset, options, value):
        """Apply `phrase` suggester.

        :param suggester_name:
        :param queryset: Original queryset.
        :param options: Filter options.
        :param value: value to filter on.
        :type suggester_name: str
        :type queryset: elasticsearch_dsl.search.Search
        :type options: dict
        :type value: str
        :return: Modified queryset.
        :rtype: elasticsearch_dsl.search.Search
        """
        return queryset.suggest(
            suggester_name,
            value,
            phrase={
                'field': options['field'],
                "direct_generator": [
                    {
                        "field": options['field'],
                        "suggest_mode": "always",
                        "min_word_length": 2,
                    }
                ]
            }
        )

    @classmethod
    def apply_suggester_term(cls, suggester_name, queryset, options, value):
        """Apply `term` suggester.

        :param suggester_name:
        :param queryset: Original queryset.
        :param options: Filter options.
        :param value: value to filter on.
        :type suggester_name: str
        :type queryset: elasticsearch_dsl.search.Search
        :type options: dict
        :type value: str
        :return: Modified queryset.
        :rtype: elasticsearch_dsl.search.Search
        """
        return queryset.suggest(
            suggester_name,
            value,
            term={'field': options['field'], "min_word_length": 2}
        )

    def get_suggester_query_params(self, request, view):
        """Get query params to be for suggestions.

        :param request: Django REST framework request.
        :param view: View.
        :type request: rest_framework.request.Request
        :type view: rest_framework.viewsets.ReadOnlyModelViewSet
        :return: Request query params to filter on.
        :rtype: dict
        """
        search_param = request.query_params.get('search')
        search_param = search_param or ''
        query_params = {
            'article_title__completion': search_param,
            'article_title_suggest__term': search_param,
            'article_title_suggest__phrase': search_param,
            'article_summary_suggest__phrase': search_param,
            'article_summary_suggest__term': search_param
        }
        query_dict = QueryDict('', mutable=True)
        query_dict.update(query_params)
        query_params = query_dict
        suggester_query_params = {}
        suggester_fields = self.prepare_suggester_fields(view)
        for query_param in query_params:
            query_param_list = self.split_lookup_filter(
                query_param,
                maxsplit=1
            )
            field_name = query_param_list[0]

            if field_name in suggester_fields:
                suggester_param = None
                if len(query_param_list) > 1:
                    suggester_param = query_param_list[1]

                valid_suggesters = suggester_fields[field_name]['suggesters']

                # If we have default suggester given use it as a default and
                # do not require further suffix specification.
                default_suggester = None
                if 'default_suggester' in suggester_fields[field_name]:
                    default_suggester = \
                        suggester_fields[field_name]['default_suggester']

                if suggester_param is None \
                        or suggester_param in valid_suggesters:

                    # If we have default suggester given use it as a default
                    # and do not require further suffix specification.
                    if suggester_param is None \
                            and default_suggester is not None:
                        suggester_param = str(default_suggester)

                    values = [
                        __value.strip()
                        for __value
                        in query_params.getlist(query_param)
                        if __value.strip() != ''
                    ]

                    if values:
                        _sf = suggester_fields[field_name]
                        suggester_query_params[query_param] = {
                            'suggester': suggester_param,
                            'values': values,
                            'field': suggester_fields[field_name].get(
                                'field',
                                field_name
                            ),
                            'type': view.mapping,
                        }

                        if 'options' in _sf:
                            if 'size' in _sf['options']:
                                suggester_query_params[query_param].update({
                                    'size': _sf['options']['size']
                                })
                            if 'skip_duplicates' in _sf['options']:
                                suggester_query_params[query_param].update({
                                    'skip_duplicates':
                                        _sf['options']['skip_duplicates']
                                })

                        if (
                            suggester_param == SUGGESTER_COMPLETION
                            and 'completion_options' in _sf
                            and (
                                'category_filters' in _sf['completion_options']
                                or
                                'geo_filters' in _sf['completion_options']
                            )
                        ):
                            suggester_query_params[query_param]['contexts'] = \
                                self.get_suggester_context(
                                    suggester_fields[field_name],
                                    suggester_param,
                                    request,
                                    view
                                )
        return suggester_query_params

    @classmethod
    def prepare_suggester_fields(cls, view):
        """Prepare filter fields.

        :param view:
        :type view: rest_framework.viewsets.ReadOnlyModelViewSet
        :return: Filtering options.
        :rtype: dict
        """
        filter_fields = {
            'article_title_suggest':
                {'field': 'title', 'suggesters': ['term', 'phrase']},
            'article_title':
                {'field': 'title.suggest', 'suggesters': ['completion']},
            'article_summary_suggest':
                {'field': 'summary', 'suggesters': ['term', 'phrase']},
            'article_tags':
                {'field': 'tags.name.suggest', 'suggesters': ['completion']},
            'article_tags_suggest':
                {'field': 'tags.name', 'suggesters': ['term', 'phrase']},
            'article_categories_suggest':
                {'field': 'categories.title', 'suggesters': ['term', 'phrase'], 'options': {
                    'size': 10,
                    'skip_duplicates': True
                }
                 },
            'article_categories':
                {'field': 'categories.title.suggest', 'suggesters': ['completion']},
        }
        return filter_fields

    def filter_queryset(self, request, queryset, view):
        """Filter the queryset.

        :param request: Django REST framework request.
        :param queryset: Base queryset.
        :param view: View.
        :type request: rest_framework.request.Request
        :type queryset: elasticsearch_dsl.search.Search
        :type view: rest_framework.viewsets.ReadOnlyModelViewSet
        :return: Updated queryset.
        :rtype: elasticsearch_dsl.search.Search
        """
        # The ``SuggesterFilterBackend`` filter backend shall be used in
        # the ``suggest`` custom view action/route only. Usages outside of the
        # are ``suggest`` action/route are restricted.
        if view.action != 'suggest':
            return queryset
        suggester_query_params = self.get_suggester_query_params(request, view)

        for suggester_name, options in suggester_query_params.items():
            value = options['values'][0]
            # We don't have multiple values here.
            if options['suggester'] == SUGGESTER_TERM:
                queryset = self.apply_suggester_term(suggester_name,
                                                     queryset,
                                                     options,
                                                     value)

            # `phrase` suggester
            elif options['suggester'] == SUGGESTER_PHRASE:
                queryset = self.apply_suggester_phrase(suggester_name,
                                                       queryset,
                                                       options,
                                                       value)

            # `completion` suggester
            elif options['suggester'] == SUGGESTER_COMPLETION:
                queryset = self.apply_suggester_completion(suggester_name,
                                                           queryset,
                                                           options,
                                                           value)

        return queryset
