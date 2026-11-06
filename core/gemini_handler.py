"""Gemini multi-dish recognition; consistent schema and defensively validated output."""
import json
import logging
import math
import os
import time
from typing import Any


MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_FOODS = 8
PROMPT_VERSION = "multifood-v2-rich-details"
logger = logging.getLogger(__name__)

# Gemini image-understanding convention: [ymin,xmin,ymax,xmax] on 0..1000.
FOOD_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "foods": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "food_name": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                    "region": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "how_to_cook": {"type": "STRING"},
                    "how_to_eat": {"type": "STRING"},
                    "origin_note": {"type": "STRING"},
                    "taste_texture": {"type": "STRING"},
                    "variations": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "ingredients": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "prep_time": {"type": "STRING"},
                    "cook_time": {"type": "STRING"},
                    "cooking_steps": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "cooking_tips": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "serving_tips": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "pairings": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "dietary_notes": {"type": "STRING"},
                    "bounding_box": {
                        "type": "ARRAY",
                        "items": {"type": "NUMBER"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                },
                "required": ["food_name", "confidence", "region", "description", "how_to_cook", "how_to_eat", "bounding_box"],
            },
        }
    },
    "required": ["foods"],
}


def _normalize_box(box: Any) -> list[float] | None:
    """Validate [ymin,xmin,ymax,xmax]; accept legacy xywh dict for migrations."""
    if isinstance(box, dict):
        try:
            x, y, w, h = (float(box[k]) for k in ("x", "y", "width", "height"))
            box = [y, x, y + h, x + w]
        except (KeyError, ValueError, TypeError):
            return None
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    try:
        vals = [float(n) for n in box]
    except (ValueError, TypeError):
        return None
    if not all(math.isfinite(n) for n in vals):
        return None
    y1, x1, y2, x2 = vals
    if not (0 <= y1 < y2 <= 1000 and 0 <= x1 < x2 <= 1000):
        return None
    return vals


def normalize_result(value: Any) -> dict:
    """Return {'foods': [...]} or {'error': ...}. Never silently discard list entries."""
    if isinstance(value, dict) and "error" in value:
        return {"error": str(value["error"])}
    if isinstance(value, dict) and "foods" in value:
        entries = value["foods"]
    elif isinstance(value, dict) and "food_name" in value:
        entries = [value]  # backward compatibility: single-dish results
    elif isinstance(value, list):
        entries = value  # backward compatibility: model returned an array
    else:
        return {"error": "Kết quả AI không có danh sách món ăn hợp lệ."}
    if not isinstance(entries, list):
        return {"error": "Trường foods phải là một danh sách."}

    foods = []
    seen = set()
    for entry in entries[:MAX_FOODS]:
        if not isinstance(entry, dict):
            continue
        name = entry.get("food_name")
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()[:120]
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        try:
            confidence = float(entry.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        if not math.isfinite(confidence):
            confidence = 0.0
        item = {"food_name": name, "confidence": round(max(0, min(100, confidence)), 1)}
        for field in ("region", "description", "how_to_cook", "how_to_eat"):
            item[field] = str(entry.get(field) or "")[:4000]
        for field in ("origin_note", "taste_texture", "prep_time", "cook_time", "dietary_notes"):
            item[field] = str(entry.get(field) or "")[:1800]
        for field in ("variations", "ingredients", "cooking_steps", "cooking_tips", "serving_tips", "pairings"):
            raw = entry.get(field)
            item[field] = [v.strip()[:550] for v in raw[:12] if isinstance(v, str) and v.strip()] if isinstance(raw, list) else []
        item["bounding_box"] = _normalize_box(entry.get("bounding_box"))
        foods.append(item)
    return {"foods": foods}


def _get_api_key() -> str | None:
    # Import Streamlit lazily so validation/tests can run without Streamlit runtime.
    import streamlit as st
    try:
        key = st.secrets["general"]["GOOGLE_API_KEY"]
    except (FileNotFoundError, KeyError, TypeError):
        return None
    return str(key).strip() or None


def _retryable(exc: Exception) -> bool:
    """Retry only rate limiting and transient server/network failures."""
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = None
    if status in (429, 500, 502, 503, 504):
        return True
    if status is not None:  # 400/401/403/404 must never be retried
        return False
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def analyze_food(image_bytes: bytes, region: str, language: str) -> dict:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    else:
        return {"error": "Ảnh phải là JPEG hoặc PNG."}
    if len(image_bytes) > 8 * 1024 * 1024:
        return {"error": "Ảnh xử lý lớn hơn 8MB. Vui lòng giảm kích thước."}
    try:
        api_key = _get_api_key()
    except Exception:
        logger.exception("Cannot read Streamlit secrets")
        return {"error": "Không thể đọc cấu hình Gemini API Key."}
    if not api_key:
        return {"error": "Thiếu [general].GOOGLE_API_KEY trong .streamlit/secrets.toml."}

    lang = "English" if language == "English" else "Vietnamese"
    prompt = (
        "You are inspecting an image of Vietnamese food. Detect up to 8 DISTINCT, clearly visible "
        "prepared dishes (not separate ingredients, garnishes, bowls, or duplicate servings). "
        "Return foods=[] when no dish can be identified; never invent food. "
        "For ambiguous dishes prefer a broader truthful label and explain uncertainty. "
        "A supplied region is only a hint; don't assume it is correct. "
        "Confidence is your subjective visual certainty score 0-100, NOT a calibrated probability. "
        "For each dish give a bounding_box [ymin,xmin,ymax,xmax] normalized 0..1000 "
        "for the entire image; use [0,0,1000,1000] only when a single dish fills the entire image. "
        "If location cannot be estimated reliably, supply [0,0,0,0] (app will discard it). "
        "Provide substantial but accurate educational detail for each detected dish. "
        "description: 80-130 words covering defining ingredients, appearance and cultural context. "
        "origin_note: regional history only when known; avoid invented origin claims. "
        "taste_texture: characteristic flavors and textures. variations: up to 3 named variants. "
        "ingredients: 5-12 typical ingredients, quantities ONLY if reasonably defensible, otherwise omit quantities. "
        "prep_time and cook_time: approximate estimates, or empty when unknown. "
        "cooking_steps: 5-8 numbered-in-order practical steps for a representative home recipe, "
        "not necessarily the exact pictured restaurant's recipe. Include safe cooking instructions for meat. "
        "cooking_tips: 2-4 practical tips. how_to_cook: a concise overview for legacy clients. "
        "how_to_eat: 60-100 words describing serving etiquette and eating method. "
        "serving_tips: 2-4 serving ideas; pairings: 1-4 common accompaniments. "
        "dietary_notes: potential allergens based on typical ingredients, clearly state actual ingredients vary. "
        "For multiple dishes, prioritize factual specificity over length; never fabricate specifics. "
        f"Region hint: {region}. All prose and dish names in {lang}. "
        "Only return JSON matching the schema."
    )
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=45000))
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=FOOD_SCHEMA,
                        temperature=0.1,
                    ),
                )
                if not response.text:
                    return {"error": "Gemini trả về nội dung trống hoặc bị chặn."}
                try:
                    data = json.loads(response.text)
                except json.JSONDecodeError:
                    return {"error": "Gemini trả về JSON không hợp lệ."}
                return normalize_result(data)
            except Exception as exc:
                if attempt < 2 and _retryable(exc):
                    logger.warning("Transient Gemini failure; retry %s (%s)", attempt + 1, type(exc).__name__)
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
                logger.warning("Gemini failed model=%s status=%s type=%s", MODEL_NAME, status, type(exc).__name__)
                if str(status) == "404":
                    return {"error": f"Model {MODEL_NAME} không khả dụng. Kiểm tra model ID và quyền API."}
                if str(status) == "429":
                    return {"error": "Gemini đang giới hạn lượt gọi (429). Thử lại sau."}
                return {"error": f"Không thể phân tích với Gemini ({type(exc).__name__}). Xem log máy chủ."}
    finally:
        # New SDKs may expose a close method; avoid holding idle HTTP sessions.
        if "client" in locals() and hasattr(client, "close"):
            client.close()
