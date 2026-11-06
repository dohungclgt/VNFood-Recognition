"""Draw multiple normalized boxes, with labels, without changing source bytes."""
import io
from PIL import Image, ImageDraw, ImageFont
from core.gemini_handler import _normalize_box

COLORS = ["#f4511e", "#00897b", "#3949ab", "#8e24aa", "#d17a00", "#c2185b", "#5d4037", "#00838f"]


def draw_bounding_boxes(image_bytes: bytes, foods: list[dict]) -> Image.Image:
    with Image.open(io.BytesIO(image_bytes)) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    line_width = max(2, round(min(width, height) * 0.006))
    font = ImageFont.load_default()
    for index, food in enumerate(foods):
        box = _normalize_box(food.get("bounding_box"))
        if box is None:
            continue
        y1, x1, y2, x2 = box
        rect = [round(x1 * width / 1000), round(y1 * height / 1000),
                round(x2 * width / 1000), round(y2 * height / 1000)]
        color = COLORS[index % len(COLORS)]
        draw.rectangle(rect, outline=color, width=line_width)
        # Index corresponds to the corresponding numbered dish details.
        label = str(index + 1)
        left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
        pad = max(3, line_width)
        tw, th = right - left, bottom - top
        tx, ty = rect[0], max(0, rect[1] - th - 2 * pad)
        draw.rectangle((tx, ty, tx + tw + 2 * pad, ty + th + 2 * pad), fill=color)
        draw.text((tx + pad, ty + pad), label, fill="white", font=font)
    return image


def draw_bounding_box(image_bytes: bytes, bbox):
    """Legacy API retained for callers from the single-food version."""
    return draw_bounding_boxes(image_bytes, [{"bounding_box": bbox}])
