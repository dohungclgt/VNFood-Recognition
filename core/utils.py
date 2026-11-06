import hashlib
import json
import os
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"
CACHE_VERSION = "v2-normalized-1000"


def get_cache_key(image_bytes: bytes, region: str = "", language: str = "", model: str = "") -> str:
    digest = hashlib.sha256()
    digest.update(CACHE_VERSION.encode())
    for value in (region, language, model):
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    digest.update(image_bytes)
    return digest.hexdigest()


def load_cache(key: str) -> Any:
    if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        return None
    path = CACHE_DIR / f"{key}.json"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return None


def save_cache(key: str, result: Any) -> None:
    if not isinstance(result, dict) or "error" in result:
        return
    if not isinstance(key, str) or len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / f"{key}.json"
    tmp = CACHE_DIR / f"{key}.{os.getpid()}.tmp"
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def clear_cache() -> None:
    if CACHE_DIR.exists():
        for file in CACHE_DIR.glob("*.json"):
            file.unlink(missing_ok=True)
