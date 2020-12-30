from django_elasticsearch_dsl_drf.serializers import DocumentSerializer

from apps.blog.documents import ArticleDocument


class ArticleDocumentSerializer(DocumentSerializer):
    class Meta:
        document = ArticleDocument
        fields = ['id', 'title', 'summary', 'categories', 'tags']
