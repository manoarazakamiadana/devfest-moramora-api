import base64
import binascii
import re

import cv2
import numpy as np
from django.conf import settings


class InvalidImageError(ValueError):
    pass


_DATA_URL_PREFIX = re.compile(r"^data:image/(?:jpeg|jpg|png);base64,", re.IGNORECASE)
_JPEG_START_OF_FRAME_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def _image_dimensions(image_bytes, is_jpeg):
    if not is_jpeg:
        if len(image_bytes) < 24 or image_bytes[12:16] != b"IHDR":
            raise InvalidImageError("The PNG image header is invalid.")
        return (
            int.from_bytes(image_bytes[16:20], "big"),
            int.from_bytes(image_bytes[20:24], "big"),
        )

    offset = 2
    while offset < len(image_bytes):
        if image_bytes[offset] != 0xFF:
            raise InvalidImageError("The JPEG image header is invalid.")
        while offset < len(image_bytes) and image_bytes[offset] == 0xFF:
            offset += 1
        if offset >= len(image_bytes):
            break
        marker = image_bytes[offset]
        offset += 1

        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(image_bytes):
            break
        segment_length = int.from_bytes(image_bytes[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(image_bytes):
            break
        if marker in _JPEG_START_OF_FRAME_MARKERS:
            if segment_length < 7:
                break
            height = int.from_bytes(image_bytes[offset + 3 : offset + 5], "big")
            width = int.from_bytes(image_bytes[offset + 5 : offset + 7], "big")
            return width, height
        if marker == 0xDA:
            break
        offset += segment_length

    raise InvalidImageError("The JPEG image header is invalid.")


def decode_image_bytes(image_bytes):
    if not image_bytes or len(image_bytes) > settings.WEBSOCKET_MAX_IMAGE_SIZE:
        raise InvalidImageError("Image is empty or exceeds the size limit.")

    is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
    is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    if not (is_jpeg or is_png):
        raise InvalidImageError("Only JPEG and PNG images are supported.")

    width, height = _image_dimensions(image_bytes, is_jpeg)
    if width <= 0 or height <= 0:
        raise InvalidImageError("Image dimensions are invalid.")
    if width * height > settings.WEBSOCKET_MAX_IMAGE_PIXELS:
        raise InvalidImageError("Image dimensions exceed the pixel limit.")

    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidImageError("The image could not be decoded.")
    height, width = image.shape[:2]
    if width * height > settings.WEBSOCKET_MAX_IMAGE_PIXELS:
        raise InvalidImageError("Image dimensions exceed the pixel limit.")
    return image


def decode_base64_image(value):
    if not isinstance(value, str):
        raise InvalidImageError("The image field must contain a Base64 string.")

    value = _DATA_URL_PREFIX.sub("", value, count=1)
    try:
        image_bytes = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidImageError("The image is not valid Base64.") from exc
    return decode_image_bytes(image_bytes)


def encode_jpeg_base64(image):
    success, encoded = cv2.imencode(".jpg", image)
    if not success:
        raise RuntimeError("The annotated image could not be encoded.")
    return base64.b64encode(encoded.tobytes()).decode("ascii")
