import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"
CACHE_VERSION = "v3-multifood-box-yxyx"
CACHE_TTL = 7 * 24 * 3600  # seconds


def get_cache_key(image_bytes: bytes, region: str = "", language: str = "", model: str = "", mode: str = "multi") -> str:
    digest = hashlib.sha256()
    for value in (CACHE_VERSION, region, language, model, mode):
        data = value.encode("utf-8")
        digest.update(len(data).to_bytes(4, "big"))
        digest.update(data)
    digest.update(image_bytes)
    return digest.hexdigest()


def _valid(key):
    return isinstance(key, str) and len(key) == 64 and all(c in "0123456789abcdef" for c in key)


def load_cache(key: str) -> Any:
    if not _valid(key):
        return None
    target = CACHE_DIR / f"{key}.json"
    try:
        if time.time() - target.stat().st_mtime > CACHE_TTL:
            return None
        with target.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError, TypeError):
        return None


def save_cache(key: str, result: Any) -> None:
    if not _valid(key) or not isinstance(result, dict) or "error" in result:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / f"{key}.json"
    tmp = CACHE_DIR / f"{key}.{os.getpid()}.tmp"
    try:
        with tmp.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, allow_nan=False, indent=2)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def clear_cache() -> None:
    if CACHE_DIR.exists():
        for file in CACHE_DIR.glob("*.json"):
            file.unlink(missing_ok=True)
