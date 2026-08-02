"""Generates QR codes as inline SVG - no Pillow/raster dependency needed."""
from __future__ import annotations

import io

import qrcode
import qrcode.image.svg


def generate_svg(data: str, box_size: int = 10) -> str:
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=box_size)
    buffer = io.BytesIO()
    img.save(buffer)
    return buffer.getvalue().decode("utf-8")
