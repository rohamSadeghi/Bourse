from django.urls import path, include
from rest_framework_swagger.views import get_swagger_view

schema_view = get_swagger_view(title="HAMI BOURSE APIs")

urlpatterns = [
    path('v1/accounts/', include("apps.accounts.api.urls")),
    path('v1/blog/', include("apps.blog.api.urls")),
    path('v1/namads/', include("apps.namads.api.urls")),
    path('v1/search/', include("apps.search_api.urls")),
    path('v1/transactions/', include("apps.transactions.api.urls")),
    path('v1/filters/', include("apps.filters.api.urls")),

    path('v1/docs/', schema_view),
]
