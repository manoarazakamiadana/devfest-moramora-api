"""
ASGI config for moramora_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "moramora_api.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator

django_asgi_app = get_asgi_application()

from django.conf import settings

from detection_ws.routing import websocket_urlpatterns


class RequireWebSocketOrigin:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket" and not any(
            name.lower() == b"origin" for name, _ in scope.get("headers", [])
        ):
            await send({"type": "websocket.close", "code": 4403})
            return
        await self.app(scope, receive, send)


websocket_app = RequireWebSocketOrigin(
    OriginValidator(
        URLRouter(websocket_urlpatterns),
        settings.WEBSOCKET_ALLOWED_ORIGINS,
    )
)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": websocket_app,
    }
)
