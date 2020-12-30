"""conf URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.cache import cache_page

from apps.blog.views import HomeView
from conf import settings

urlpatterns = [
    path('adminD9B87D/', admin.site.urls),
    path('taggit-autosuggest/', include('taggit_autosuggest.urls')),

    # Template views
    # TODO: enable cache on production release date just for home view
    path('', HomeView.as_view(), name='home'),
    # path('', cache_page(2 * 60 * 60)(HomeView.as_view()), name='home'),
    path('articles/', include('apps.blog.urls')),
    path('transactions/', include('apps.transactions.urls')),

    # API views
    path('api/', include("apps.urls_api")),
]

if settings.DEVEL:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
