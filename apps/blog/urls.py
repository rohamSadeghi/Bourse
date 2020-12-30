from django.urls import path, re_path
from django.views.decorators.cache import cache_page

from apps.blog.views import ArticleDetailView, ArticleListView, article_content_view

app_name = 'blog'

urlpatterns = [
    path('content/<int:pk>/', article_content_view, name='article-content'),
    # TODO: enable cache on production release date
    # re_path(r'^detail/(?P<pk>\d+)/(.+/)?$', cache_page(2 * 60 * 60)(ArticleDetailView.as_view()), name='article-detail'),
    # re_path(r'^(?P<category_id>\d+)/(.+/)?$', cache_page(2 * 60 * 60)(ArticleListView.as_view()), name='article-list'),
    re_path(r'^detail/(?P<pk>\d+)/(.+/)?$', ArticleDetailView.as_view(), name='article-detail'),
    re_path(r'^(?P<category_id>\d+)/(.+/)?$', ArticleListView.as_view(), name='article-list'),
]
