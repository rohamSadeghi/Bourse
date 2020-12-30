from django.urls import path, include
from rest_framework import routers

from apps.blog.api.views import CategoryViewSet, ArticleViewSet, ArticleCommentViewSet

router = routers.SimpleRouter()
router.register(r'categories', CategoryViewSet, basename='categories')
router.register(r'comments', ArticleCommentViewSet, basename='article-comments')
router.register(r'articles', ArticleViewSet, basename='articles')

urlpatterns = [
    path('', include(router.urls)),
]
