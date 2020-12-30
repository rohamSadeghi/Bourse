from ckeditor.widgets import CKEditorWidget

from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.blog.models import Category, Article, ArticleComment
from apps.commenting.admin import BaseCommentAdmin


class ArticleForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Article
        fields = '__all__'


class ApprovedListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('approved')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'approved'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('approved', _('approved')),
            ('not-approved', _('not approved')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # to decide how to filter the queryset.
        if self.value() == 'approved':
            queryset = queryset.exclude(approved_user__isnull=True)
            return queryset
        if self.value() == 'not-approved':
            queryset = queryset.filter(approved_user__isnull=True)
            return queryset


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "sort_by", "parent", "created_time", "is_enable")
    search_fields = ('title', 'slug')
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ('parent', )
    autocomplete_fields = ('parent', )


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "profile", "slug", "is_approved", "created_time", "is_enable")
    list_select_related = ['profile', ]
    search_fields = ('title', 'slug')
    autocomplete_fields = ('categories', 'namads', 'profile')
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ('is_enable', ApprovedListFilter, 'categories')
    actions = ['set_approved', 'set_unapproved']
    form = ArticleForm

    def set_approved(self, request, queryset):
        queryset.filter(
            approved_user__isnull=True
        ).update(
            approved_user=request.user,
            approved_time=timezone.now()
        )

    def set_unapproved(self, request, queryset):
        queryset.filter(
            approved_user__isnull=False
        ).update(
            approved_user=None,
            approved_time=None
        )


@admin.register(ArticleComment)
class ArticleCommentAdmin(BaseCommentAdmin):
    list_display = ["user", "article", "is_approved", "created_time", "is_enable"]
    search_fields = ('article__title', 'article__slug')
