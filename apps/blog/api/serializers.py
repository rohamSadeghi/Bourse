from django.conf import settings
from django.templatetags.static import static

from rest_framework import serializers
from rest_framework.reverse import reverse as api_reverse

from sorl.thumbnail import get_thumbnail

from apps.accounts.api.serializers import UserProfileSerializer
from apps.blog.models import Category, Article, ArticleRate, ArticleBookmark, ArticleComment
from apps.commenting.api.serializers import BaseCommentSerializer
from apps.namads.models import Namad

ARTICLE_DEFAULT_IMAGE_PATH = static('blog/Default-article.png')


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'title', 'slug', 'created_time',  'children')

    def get_children(self, obj):
        return CategorySerializer(obj.children.filter(is_enable=True), many=True).data


class NamadSerializer(serializers.ModelSerializer):
    namad_url = serializers.SerializerMethodField()

    class Meta:
        model = Namad
        fields = ('id', 'name', 'title', 'group_name', 'description', 'namad_url', 'created_time')

    def get_namad_url(self, obj):
        request = self.context.get('request')
        if request:
            return api_reverse('namads-detail', kwargs={"pk": obj.id}, request=request)


class ArticleSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        remove_fields = kwargs.pop('remove_fields', None)
        super(ArticleSerializer, self).__init__(*args, **kwargs)

        if remove_fields:
            # for multiple fields in a list
            for field_name in remove_fields:
                self.fields.pop(field_name, None)

    author_profile = UserProfileSerializer(
        remove_fields=['gender', 'birth_date', 'email_address', 'has_password'],
        read_only=True,
        source='profile'
    )
    content_url = serializers.SerializerMethodField()
    rating_avg = serializers.DecimalField(read_only=True, max_digits=2, decimal_places=1)
    rating_count = serializers.IntegerField(read_only=True)
    user_rate = serializers.SerializerMethodField()
    user_bookmark = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    namads = NamadSerializer(many=True)
    thumbnail_image = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'slug', 'author_profile', 'summary', 'lead',
            'is_free', 'image', 'thumbnail_image', 'video_url', 'content_url',
            'categories', 'tags', 'namads', 'user_rate', 'user_bookmark',
            'created_time', 'approved_time', 'rating_avg', 'rating_count', 'views_count'
        )

    def get_content_url(self, obj):
        view = self.context.get('view')

        if view and view.action == 'list':
            return
        return api_reverse("blog:article-content", kwargs={"pk": obj.pk}, request=self.context['request'])

    def get_user_rate(self, obj):
        user = self.context['request'].user

        if user.is_authenticated and self.context['view'].action == 'retrieve':
            try:
                return ArticleRate.objects.get(user=self.context['request'].user, article=obj).rate
            except ArticleRate.DoesNotExist:
                return

    def get_user_bookmark(self, obj):
        user = self.context['request'].user

        if user.is_authenticated and self.context['view'].action == 'retrieve':
            try:
                return ArticleBookmark.objects.get(
                    user=user,
                    article=obj,
                ).status
            except ArticleBookmark.DoesNotExist:
                return False
        return False

    def get_tags(self, obj):
        return obj.tags.names()

    def get_thumbnail_image(self, obj):
        request = self.context['request']
        image = obj.image

        if image:
            image = get_thumbnail(image, settings.ARTICLE_THUMBNAIL_SIZE, crop='center', quality=99)
        else:
            image_url = request.build_absolute_uri(ARTICLE_DEFAULT_IMAGE_PATH)
            image = get_thumbnail(image_url, settings.ARTICLE_THUMBNAIL_SIZE, crop='center', quality=99)
        return request.build_absolute_uri(image.url)

    def get_image(self, obj):
        request = self.context['request']

        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return request.build_absolute_uri(ARTICLE_DEFAULT_IMAGE_PATH)


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleRate
        fields = ('id', 'rate', 'created_time')
        read_only_fields = ('id', 'created_time', )

    def create(self, validated_data):
        rate = validated_data.pop('rate')
        instance, _created = ArticleRate.objects.update_or_create(
            **validated_data,
            defaults={'rate': rate}
        )
        return instance


class BookmarkSerializer(serializers.ModelSerializer):
    article = ArticleSerializer(read_only=True)

    class Meta:
        model = ArticleBookmark
        fields = ('id', 'article', 'status', 'created_time')
        read_only_fields = ('id', 'created_time', 'article')

    def create(self, validated_data):
        status = validated_data.pop('status', False)
        instance, _created = ArticleBookmark.objects.update_or_create(
            **validated_data,
            defaults={'status': status}
        )
        return instance


class ArticleCommentSerializer(BaseCommentSerializer):

    class Meta:
        model = ArticleComment
        base_fields = BaseCommentSerializer.Meta.fields
        base_fields.append('article')
        base_read_only_fields = BaseCommentSerializer.Meta.read_only_fields
        base_read_only_fields.append('article')
        fields = base_fields
        read_only_fields = base_read_only_fields
