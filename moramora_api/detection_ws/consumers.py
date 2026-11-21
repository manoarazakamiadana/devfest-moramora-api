import asyncio
import base64
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from detection_ws.image_adapter import (
    InvalidImageError,
    decode_base64_image,
    decode_image_bytes,
    encode_jpeg_base64,
)
from detection_ws.services.violation_service import process_image
from violation.inference import DetectorBusyError

logger = logging.getLogger(__name__)
_MAX_BASE64_MESSAGE_SIZE = (settings.WEBSOCKET_MAX_IMAGE_SIZE + 2) // 3 * 4 + 4096


class DetectionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(code=4401)
            return
        if self.scope["auth_via_subprotocol"]:
            await self.accept(subprotocol="bearer")
        else:
            await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if bytes_data is not None:
                image = await asyncio.to_thread(decode_image_bytes, bytes_data)
            elif text_data is not None:
                if len(text_data.encode("utf-8")) > _MAX_BASE64_MESSAGE_SIZE:
                    raise InvalidImageError("Image message exceeds the size limit.")
                image = await asyncio.to_thread(self._decode_json_image, text_data)
            else:
                raise InvalidImageError("An image message is required.")
        except (InvalidImageError, json.JSONDecodeError) as exc:
            await self._send_error(str(exc))
            return

        try:
            annotated_image, detections = await asyncio.to_thread(process_image, image)
            encoded_image = await asyncio.to_thread(
                encode_jpeg_base64,
                annotated_image,
            )
        except DetectorBusyError:
            await self._send_error(
                "The detection engine is busy; retry this image later.",
                code="busy",
            )
            return
        except Exception:
            logger.exception("Image detection failed.")
            await self._send_error("Image processing failed.", code="processing_error")
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "detection_result",
                    "success": True,
                    "data": {
                        "image": encoded_image,
                        "detections": detections,
                        "message": "Image processed successfully",
                    },
                }
            )
        )
        if detections:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "alert",
                        "event": "DETECTION_ALERT",
                        "message": "A violation has been detected",
                        "data": {"detections": detections},
                    }
                )
            )

    @staticmethod
    def _decode_json_image(text_data):
        message = json.loads(text_data)
        if not isinstance(message, dict) or message.get("type") != "image":
            raise InvalidImageError('Expected a JSON message with type "image".')
        return decode_base64_image(message.get("image"))

    async def _send_error(self, message, code="invalid_image"):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "error",
                    "success": False,
                    "code": code,
                    "message": message,
                }
            )
        )
