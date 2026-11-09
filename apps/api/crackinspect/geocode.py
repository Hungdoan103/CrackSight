from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .config import STORE_DIR

CACHE_PATH = STORE_DIR / "geocode_cache.json"
_USER_AGENT = "CrackInspect/0.1 (infrastructure inspection; contact=local)"
_last_call = 0.0
_MIN_INTERVAL = 1.05  # Nominatim fair-use: ≤1 req/s

def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}

def _save_cache(cache: dict) -> None:
    try:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _cache_key(lat: float, lon: float, lang: str) -> str:
    return f"{round(lat, 5):.5f},{round(lon, 5):.5f}:{lang}"

def _format_address(payload: dict) -> str:
    addr = payload.get("address") if isinstance(payload.get("address"), dict) else {}
    road = (
        addr.get("road")
        or addr.get("pedestrian")
        or addr.get("path")
        or addr.get("footway")
        or addr.get("residential")
        or ""
    )
    suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter") or ""
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or addr.get("county")
        or ""
    )
    state = addr.get("state") or addr.get("region") or ""
    postcode = addr.get("postcode") or ""
    country = addr.get("country") or ""

    parts: list[str] = []
    if road:
        house = addr.get("house_number") or ""
        parts.append(f"{house} {road}".strip() if house else road)
    if suburb and suburb not in parts:
        parts.append(suburb)
    city_line = " ".join(x for x in (city, state, postcode) if x).strip()
    if city_line:
        parts.append(city_line)
    elif country:
        parts.append(country)

    if parts:
        return ", ".join(parts)
    display = str(payload.get("display_name") or "").strip()
    return display

def reverse_geocode(lat: float, lon: float, lang: str = "en") -> str:
    global _last_call
    lang = "vi" if str(lang).lower().startswith("vi") else "en"
    key = _cache_key(lat, lon, lang)
    cache = _load_cache()
    hit = cache.get(key)
    if isinstance(hit, str) and hit:
        return hit

    wait = _MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)

    params = urllib.parse.urlencode(
        {
            "format": "jsonv2",
            "lat": f"{lat:.7f}",
            "lon": f"{lon:.7f}",
            "zoom": "18",
            "addressdetails": "1",
        }
    )
    url = f"https://nominatim.openstreetmap.org/reverse?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "vi,en" if lang == "vi" else "en",
        },
        method="GET",
    )
    try:
        _last_call = time.monotonic()
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return ""

    if not isinstance(payload, dict):
        return ""
    address = _format_address(payload)
    if address:
        cache[key] = address
        _save_cache(cache)
    return address

def reverse_geocode_many(
    points: list[tuple[float, float]],
    lang: str = "en",
) -> list[str]:
    return [reverse_geocode(lat, lon, lang=lang) for lat, lon in points]
