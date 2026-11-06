import json
import logging
from typing import Any

import streamlit as st
from google import genai
from google.genai import types

MODEL_NAME = "gemini-3.5-flash-lite"
logger = logging.getLogger(__name__)


def normalize_result(value: Any) -> dict:
    """Force Gemini/cache output to a single canonical dish dictionary."""
    if isinstance(value, list):
        value = next((item for item in value if isinstance(item, dict)), None)
    if not isinstance(value, dict):
        return {"error": "AI trả về dữ liệu không hợp lệ (cần JSON object)."}
    if "error" in value:
        return {"error": str(value["error"])}
    if "raw_output" in value:
        return {"error": "AI không trả về dữ liệu có cấu trúc hợp lệ."}
    if not isinstance(value.get("food_name"), str) or not value["food_name"].strip():
        return {"error": "AI không xác định được tên món ăn."}
    box = value.get("bounding_box")
    if isinstance(box, list) and len(box) == 4:
        box = dict(zip(("x", "y", "width", "height"), box))
    if not isinstance(box, dict):
        box = None
    fields = ("region", "description", "how_to_cook", "how_to_eat")
    result = {"food_name": value["food_name"].strip()}
    for field in fields:
        result[field] = str(value.get(field) or "")
    try:
        confidence = float(value.get("confidence", 0))
        result["confidence"] = max(0, min(100, confidence))
    except (TypeError, ValueError):
        result["confidence"] = 0
    result["bounding_box"] = box
    return result


def analyze_food(image_bytes: bytes, region: str, language: str) -> dict:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    else:
        return {"error": "Ảnh phải ở định dạng PNG hoặc JPEG."}

    try:
        api_key = st.secrets["general"]["GOOGLE_API_KEY"]
        if not api_key or not str(api_key).strip():
            return {"error": "GOOGLE_API_KEY đang trống trong secrets.toml."}
    except (FileNotFoundError, KeyError, TypeError):
        return {"error": "Thiếu [general].GOOGLE_API_KEY trong .streamlit/secrets.toml."}

    is_en = language == "English"
    prompt = (
        f"Identify the main Vietnamese food in this image. Region hint: {region}. "
        f"Respond in {'English' if is_en else 'Vietnamese'}. "
        "Output ONE JSON object (not an array) with keys: food_name, confidence "
        "(number from 0 to 100), region, description, how_to_cook, how_to_eat, "
        "bounding_box (object with x,y,width,height). Bounding box values must "
        "use 0..1000 normalized coordinates relative to the entire image, "
        "with x,y being the top-left corner. If the bounding box cannot be "
        "reliably determined, use null. Do not blindly assume the region hint is correct."
    )
    schema = {
        "type": "OBJECT",
        "properties": {
            "food_name": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
            "region": {"type": "STRING"},
            "description": {"type": "STRING"},
            "how_to_cook": {"type": "STRING"},
            "how_to_eat": {"type": "STRING"},
            "bounding_box": {
                "type": "OBJECT",
                "nullable": True,
                "properties": {
                    "x": {"type": "NUMBER"},
                    "y": {"type": "NUMBER"},
                    "width": {"type": "NUMBER"},
                    "height": {"type": "NUMBER"},
                },
                "required": ["x", "y", "width", "height"],
            },
        },
        "required": ["food_name", "confidence", "region", "description", "how_to_cook", "how_to_eat", "bounding_box"],
    }
    try:
        logger.info("Calling Gemini model: %s", MODEL_NAME)
        client = genai.Client(api_key=str(api_key).strip())
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
        if not response.text:
            return {"error": "Gemini trả về phản hồi trống."}
        return normalize_result(json.loads(response.text))
    except json.JSONDecodeError:
        return {"error": "Gemini trả về JSON không hợp lệ."}
    except Exception as exc:
        logger.exception("Gemini analysis failed")
        return {"error": f"Lỗi Gemini ({MODEL_NAME}): {exc}"}
