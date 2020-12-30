from django.urls import path, include
from rest_framework import routers

from apps.namads.api.views import NamadViewSet, NamadCommentViewSet

router = routers.SimpleRouter()
router.register(r'comments', NamadCommentViewSet, basename='namad-comments')
router.register(r'', NamadViewSet, basename='namads')

urlpatterns = [
    path('', include(router.urls)),
]
