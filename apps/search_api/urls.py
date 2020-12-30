from django.urls import path, include
from rest_framework import routers

from apps.search_api.views import ArticleSearchViewSet

router = routers.SimpleRouter()
router.register(r'', ArticleSearchViewSet, basename='search')

urlpatterns = [
    path('', include(router.urls), ),
]
