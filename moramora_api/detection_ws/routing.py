from django.urls import path

from detection_ws.consumers import DetectionConsumer
from detection_ws.authentication import JWTAuthMiddleware

websocket_urlpatterns = [
    path(
        "ws/detection/",
        JWTAuthMiddleware(DetectionConsumer.as_asgi()),
    ),
]
