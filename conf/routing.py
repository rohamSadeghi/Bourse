from django.urls import path

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from apps.filters.consumer import FilterConsumer


asgi_routes = {
    "websocket": AuthMiddlewareStack(
        URLRouter(
            [
                path('filter-signal/', FilterConsumer),
            ]
        )
    )
}
