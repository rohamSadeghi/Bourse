from django.urls import path, include
from rest_framework import routers

from apps.transactions.api.views import PackageViewSet, PurchasePackageViewSet

router = routers.SimpleRouter()
router.register(r'packages', PackageViewSet, basename='packages')
router.register(r'purchase-packages', PurchasePackageViewSet, basename='purchase-packages')

urlpatterns = [
    path('', include(router.urls)),
]
