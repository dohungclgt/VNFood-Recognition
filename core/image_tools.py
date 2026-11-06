import io
import math
from typing import Any

from PIL import Image, ImageDraw


def draw_bounding_box(image_bytes: bytes, bbox: Any) -> Image.Image:
    """Draw a normalized 0..1000 (x,y,width,height) box; return unchanged image if invalid."""
    with Image.open(io.BytesIO(image_bytes)) as source:
        image = source.convert("RGB")

    if isinstance(bbox, list) and len(bbox) == 4:
        bbox = dict(zip(("x", "y", "width", "height"), bbox))
    if not isinstance(bbox, dict):
        return image
    try:
        x, y, w, h = (float(bbox[k]) for k in ("x", "y", "width", "height"))
    except (KeyError, ValueError, TypeError):
        return image
    if not all(math.isfinite(v) for v in (x, y, w, h)):
        return image
    if not (0 <= x <= 1000 and 0 <= y <= 1000 and 0 < w <= 1000 and 0 < h <= 1000):
        return image
    if x + w > 1000 or y + h > 1000:
        return image

    width, height = image.size
    left = round(x * width / 1000)
    top = round(y * height / 1000)
    right = round((x + w) * width / 1000)
    bottom = round((y + h) * height / 1000)
    if right <= left or bottom <= top:
        return image
    line_width = max(2, round(min(width, height) * 0.006))
    ImageDraw.Draw(image).rectangle((left, top, right, bottom), outline="#ff4d00", width=line_width)
    return image
