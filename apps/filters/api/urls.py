from django.urls import path, include
from rest_framework import routers

from apps.filters.api.views import RegisterFilterAPIView, InitialFilterAPIView, FilterCategoryView

router = routers.SimpleRouter()
router.register(r'categories', FilterCategoryView, basename='filter-categories')

urlpatterns = [
    path('', include(router.urls)),
    path('initial-filter/<int:category_id>/', InitialFilterAPIView.as_view(), name='initial-filter'),
    path('register-filter/', RegisterFilterAPIView.as_view(), name='register-filter'),
]
