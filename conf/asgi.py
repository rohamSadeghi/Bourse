"""
ASGI config for django_3 project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""
import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')
django_asgi_app = get_asgi_application()

from django.conf import settings

from .routing import asgi_routes

if not settings.DEVEL:
    asgi_routes["http"] = django_asgi_app

application = ProtocolTypeRouter(asgi_routes)
