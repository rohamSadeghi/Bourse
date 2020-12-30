from django.conf import settings

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import analyzer

from .models import Article

html_strip = analyzer(
    'html_strip',
    tokenizer="keyword",
    filter=["lowercase", "stop", "snowball","arabic_normalization", "shingle"],
    char_filter=["html_strip"]
)


@registry.register_document
class ArticleDocument(Document):
    id = fields.IntegerField()
    title = fields.TextField(
        fields={
            'raw': fields.TextField(analyzer=html_strip),
            'suggest': fields.CompletionField(analyzer=html_strip),
        }
    )

    tags = fields.ObjectField(
        properties={
            "name": fields.TextField(
                fields={
                    'raw': fields.TextField(analyzer=html_strip),
                    'suggest': fields.CompletionField(),
                }
            )
        }
    )
    categories = fields.ObjectField(
        properties={
            'id': fields.IntegerField(),
            'title': fields.TextField(
                fields={
                    'raw': fields.TextField(analyzer=html_strip),
                    'suggest': fields.CompletionField(),
                }
            ),
            'slug': fields.TextField(analyzer=html_strip)
        }
    )

    class Index:
        name = settings.ARTICLE_INDEX_NAME
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 0
        }

    def get_queryset(self):
        return super(ArticleDocument, self).get_queryset().filter(
            approved_user__isnull=False,
            is_enable=True
        ).prefetch_related(
            'tags',
            'categories',
            'namads'
        )

    class Django:
        model = Article
        fields = ['summary', ]
