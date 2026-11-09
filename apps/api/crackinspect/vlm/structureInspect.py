from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .ollamaClient import chat_vision

STRUCTURE_SYSTEM = (
    "You are a bridge/field structural inspection assistant. "
    "Ground every field on what is visible in the photo. "
    "Do not invent GPS, millimeters, or unobserved defects. "
    "Reply with JSON only."
)

STRUCTURE_PROMPT = (
    "Phân tích hình ảnh hiện trường kết cấu cầu này và trích xuất thông tin "
    "dưới dạng cấu trúc JSON với các trường sau:\n\n"
    "structural_element: (Ví dụ: steel girder, bearing pad, concrete pier, bolt/anchor)\n\n"
    "defect_type: (Danh sách các lỗi: severe corrosion, concrete spalling, cracking, "
    "rust staining, missing hardware)\n\n"
    "severity_level: (Low / Medium / High / Critical)\n\n"
    "location_description: (Mô tả vị trí xuất hiện hư hỏng trên cấu kiện)\n\n"
    "recommended_action: (Đề xuất sơ bộ như: cleaning, coating, repair, replacement)\n\n"
    "Reply JSON only with exactly these keys. "
    "defect_type may be a string or an array of strings from the allowed list "
    "(or closest visible defects). "
    "If no defect is visible, set defect_type to [] or \"none\", "
    "severity_level to \"Low\", and recommended_action to \"monitor\"."
)

_SEVERITY = {"low", "medium", "high", "critical"}
_KEYS = (
    "structural_element",
    "defect_type",
    "severity_level",
    "location_description",
    "recommended_action",
)

def _usable_json(blob: str) -> dict[str, Any] | None:
    text = (blob or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None

def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out["structural_element"] = str(data.get("structural_element") or "").strip() or "unknown"

    defects = data.get("defect_type")
    if isinstance(defects, list):
        out["defect_type"] = [str(x).strip() for x in defects if str(x).strip()]
    elif defects is None or str(defects).strip().lower() in {"", "none", "null"}:
        out["defect_type"] = []
    else:
        parts = re.split(r"[,;/|]", str(defects))
        out["defect_type"] = [p.strip() for p in parts if p.strip()]

    sev = str(data.get("severity_level") or "Low").strip()
    sev_norm = sev.title() if sev.lower() in _SEVERITY else sev
    if sev.lower() in _SEVERITY:
        sev_norm = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}[sev.lower()]
    out["severity_level"] = sev_norm

    out["location_description"] = str(data.get("location_description") or "").strip()
    out["recommended_action"] = str(data.get("recommended_action") or "").strip()
    return out

def _fallback(ctx: dict) -> dict[str, Any]:
    kind = ctx.get("scene_kind") or ""
    det = str(ctx.get("detector") or "")
    if kind == "hientruong" or det.startswith("lcw"):
        element = "concrete pier"
    else:
        element = "concrete surface"
    n = len(ctx.get("instances") or [])
    has = bool(ctx.get("real_detection") or n or ctx.get("has_crack"))
    if has:
        return {
            "structural_element": element,
            "defect_type": ["cracking"],
            "severity_level": "Medium",
            "location_description": "Visible crack indicators on the structure surface in frame.",
            "recommended_action": "repair",
        }
    return {
        "structural_element": element,
        "defect_type": [],
        "severity_level": "Low",
        "location_description": "No clear structural defect visible in this photo.",
        "recommended_action": "monitor",
    }

def prose_from_structure(report: dict[str, Any], *, lang: str = "vi") -> str:
    element = report.get("structural_element") or "unknown"
    defects = report.get("defect_type") or []
    if isinstance(defects, list):
        defect_txt = ", ".join(defects) if defects else ("không rõ" if lang == "vi" else "none")
    else:
        defect_txt = str(defects)
    sev = report.get("severity_level") or "Low"
    loc = report.get("location_description") or ""
    act = report.get("recommended_action") or ""
    if lang == "en":
        return (
            f"Structural element: {element}. Defects: {defect_txt}. "
            f"Severity: {sev}. Location: {loc or 'n/a'}. "
            f"Recommended action: {act or 'n/a'}."
        )
    return (
        f"Cấu kiện: {element}. Hư hỏng: {defect_txt}. "
        f"Mức độ: {sev}. Vị trí: {loc or 'không rõ'}. "
        f"Đề xuất: {act or 'theo dõi'}."
    )

def extract_structure_report(ctx: dict) -> dict[str, Any]:
    path = Path(ctx.get("image_path") or "")
    if not path.is_file():
        return _fallback(ctx)

    def _call(*, think: bool, num_predict: int) -> dict[str, Any] | None:
        try:
            raw = chat_vision(
                STRUCTURE_PROMPT,
                [path],
                system=STRUCTURE_SYSTEM,
                think=think,
                num_predict=num_predict,
                fallback_short=False,
                extract=False,
                json_format=True,
            )
        except Exception:
            return None
        data = _usable_json(raw or "")
        if not data:
            return None
        if not any(str(data.get(k) or "").strip() for k in _KEYS):
            return None
        return _normalize(data)

    # One short VL pass — avoid think/retry (2× latency on 8GB laptops).
    parsed = _call(think=False, num_predict=360)
    return parsed if parsed is not None else _fallback(ctx)
