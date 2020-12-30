from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.functions import Coalesce
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from taggit_autosuggest.managers import TaggableManager

from apps.commenting.models import AbstractComment, AbstractCommentVote
from utils.utils import article_directory_path, ApprovedManager, JalaliTimeMixin

HAMI_BOURSE_LOGO_PATH = static('blog/HamiBourse-logo.jpg')


class ParentCategoryManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(parent__isnull=True)


class Category(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    title = models.CharField(_('title'), max_length=50)
    slug = models.SlugField(_('slug'), max_length=50, unique=True, allow_unicode=True)
    parent = models.ForeignKey('self', blank=True, null=True, on_delete=models.CASCADE, related_name="children", verbose_name=_("parent"))
    description = models.TextField(_('description'), blank=True)
    sort_by = models.PositiveSmallIntegerField(_('sort'), default=0)
    is_enable = models.BooleanField(_("is enable"), default=True)
    objects = models.Manager()
    parents = ParentCategoryManager()

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['sort_by', 'id']

    def __str__(self):
        return self.slug

    def clean(self):
        super(Category, self).clean()

        if (self.parent and self.parent.parent == self) or self.parent == self:
            raise ValidationError(_("This category is somehow a child category and can not be parent again"))

    def get_absolute_url(self):
        return f"{reverse('blog:article-list', kwargs={'category_id': self.id})}{self.slug}/"

    @classmethod
    def category_tree(cls, cat_parent=None):
        qs = cls.objects.filter(is_enable=True)
        if cat_parent is None:
            qs = qs.filter(parent__isnull=True)
        else:
            qs = qs.filter(parent=cat_parent)

        cat_list = []
        for cat in qs:
            cat_dict = {
                "category": cat,
                "subs": cls.category_tree(cat)
            }

            if not cat_dict["subs"]:
                cat_dict["articles"] = Article.approves.filter(categories=cat)[:3]

            cat_list.append(cat_dict)

        return cat_list


class Article(models.Model, JalaliTimeMixin):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    profile = models.ForeignKey('accounts.UserProfile', verbose_name=_('profile'), on_delete=models.PROTECT)
    approved_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('approved user'), blank=True, null=True, editable=False, on_delete=models.CASCADE, related_name='article_approved_users')
    approved_time = models.DateTimeField(_('approved time'), blank=True, null=True, db_index=True)
    title = models.CharField(_('title'), max_length=120)
    image = models.ImageField(_('image'), upload_to=article_directory_path)
    video_url = models.CharField(_('video URL'), blank=True, max_length=150)
    slug = models.SlugField(_('slug'), max_length=50, unique=True, allow_unicode=True)
    content = models.TextField(_('content'))
    summary = models.TextField(_('summary'))
    lead = models.CharField(_('lead'), max_length=200)
    views_count = models.PositiveIntegerField(verbose_name=_('views count'), default=int, editable=False)
    is_free = models.BooleanField(_('is free'), default=True)
    is_enable = models.BooleanField(_('is enable'), default=True)

    tags = TaggableManager(verbose_name=_('tags'), related_name='articles')
    categories = models.ManyToManyField('Category', verbose_name=_('categories'), related_name='articles')
    namads = models.ManyToManyField('namads.Namad', verbose_name=_('namads'), related_name='articles', blank=True)

    objects = models.Manager()
    approves = ApprovedManager()

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ('-id', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rating_data = None

    def __str__(self):
        return self.slug

    # Following method and attribute is used in admin page for showing tick or cross
    def is_approved(self):
        return self.approved_time is not None and self.approved_user is not None
    is_approved.boolean = True

    @property
    def sd(self):
        # Structured data to use in article detail for SEO purpose.
        # Note: It has to be property. Do not remove property decorator.
        return {
            "@context": "https://schema.org",
            "@type": 'Article',
            "headline": self.title,
            "image": self.image.url,
            "description": self.summary,
            "name": self.title,
            "author": {
                "@type": "Person",
                "name": self.profile.full_name
            },
            "datePublished": (self.approved_time or timezone.now()).isoformat(),
            "publisher": {
                "@type": "Organization",
                "name": "HamiBourse",
                "logo": {
                    "@type": "ImageObject",
                    "url": HAMI_BOURSE_LOGO_PATH
                }
            },
            "dateModified": self.updated_time.isoformat(),
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": str(self.rating_avg()),
                "reviewCount": str(self.rating_count())
            }
        }

    def get_absolute_url(self):
        return f"{reverse('blog:article-detail', kwargs={'pk': self.id})}{self.slug}/"

    def get_rating_data(self):
        if self._rating_data is None:
            self._rating_data = ArticleRate.objects.filter(article=self).aggregate(
                avg=Coalesce(models.Avg('rate'), 0),
                count=models.Count('id')
            )
            self._rating_data['avg'] = round(self._rating_data['avg'], 1)
        return self._rating_data

    def rating_avg(self):
        rating_data = self.get_rating_data()
        return rating_data['avg']

    def rating_count(self):
        rating_data = self.get_rating_data()
        return rating_data['count']


class ArticleBookmark(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name='bookmarks', on_delete=models.CASCADE)
    article = models.ForeignKey('Article', verbose_name=_('article'), related_name='bookmarks', on_delete=models.CASCADE)
    status = models.BooleanField(verbose_name=_('status'), default=True)

    class Meta:
        verbose_name = _("Article bookmark")
        verbose_name_plural = _("Article bookmarks")
        constraints = [
            models.UniqueConstraint(fields=['user', 'article'], name='unique user_article_favorite')
        ]

    def __str__(self):
        return f"{str(self.user)}->{str(self.article)}"


class ArticleRate(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name='rates', on_delete=models.CASCADE)
    article = models.ForeignKey('Article', verbose_name=_('article'), related_name='rates', on_delete=models.CASCADE)
    rate = models.PositiveSmallIntegerField(_("rate"), validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        verbose_name = _("Article rate")
        verbose_name_plural = _("Article rates")
        constraints = [
            models.UniqueConstraint(fields=['user', 'article'], name='unique user_article_rate')
        ]

    def __str__(self):
        return f"user: {str(self.user)}->article: {str(self.article)}, rate: {str(self.rate)}"


class ArticleComment(AbstractComment):
    article = models.ForeignKey('Article', verbose_name=_('article'), related_name='comments', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Article comment")
        verbose_name_plural = _("Article comments")

    def __str__(self):
        return f"user: {str(self.user)}->article: {str(self.article)}"

    @property
    def get_full_name(self):
        if hasattr(self.user, 'profile'):
            return self.user.profile.full_name
        return ""


class ArticleCommentVote(AbstractCommentVote):
    comment = models.ForeignKey("ArticleComment", on_delete=models.CASCADE, related_name="votes", verbose_name=_("comment"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['comment', 'user'], name='article_user_comment_vote')
        ]
        verbose_name = _("Comment vote")
        verbose_name_plural = _("Comment votes")

    def __str__(self):
        return f"comment: {str(self.comment)}->vote: {str(self.vote)}"
