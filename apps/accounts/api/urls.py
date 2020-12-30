from django.urls import path, include
from rest_framework import routers

from apps.accounts.api.views import (
    TokenObtainPairView,
    TokenRefreshView,
    RegisterAPIView,
    SetPasswordAPIView,
    ChangePasswordAPIView,
    ForgetPasswordAPIView,
    ProfileViewSet
)

router = routers.SimpleRouter()
router.register(r'profile', ProfileViewSet, basename='profile')

urlpatterns = [
    path('token/obtain/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('set-password/', SetPasswordAPIView.as_view(), name='set-password'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change-password'),
    path('forget-password/', ForgetPasswordAPIView.as_view(), name='forget-password'),

    path('', include(router.urls)),
]
