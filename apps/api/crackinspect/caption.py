from __future__ import annotations

import json
import re
from pathlib import Path

from .config import SOURCE_KINDS
from .ollamaClient import chat_vision
from .summarize import gate_vl_text

CAPTION_SYSTEM = (
    "You inspect road survey photos. Write a short grounded scene description "
    "like a field engineer briefing a manager. No bounding boxes. "
    "Do not invent GPS numbers, millimeters, or area."
)

def _usable(text: str) -> bool:
    value = (text or "").strip()
    return len(value) > 20 and value not in {
        "...",
        "…",
        "mo ta tieng Viet",
        "English description",
        "mô tả tiếng Việt",
    }

def _quoted(blob: str, key: str) -> str | None:
    best = ""
    for match in re.finditer(rf'"{key}"\s*:\s*"((?:\\.|[^"\\])*)"', blob or ""):
        try:
            value = json.loads(f'"{match.group(1)}"')
        except json.JSONDecodeError:
            value = match.group(1).replace("\\n", " ").strip()
        if _usable(value) and len(value) > len(best):
            best = value
    return best or None

def parse_caption(raw: str) -> tuple[str, str]:
    vi = (_quoted(raw, "description_vi") or "").strip()
    en = (_quoted(raw, "description_en") or "").strip()
    if _usable(vi) or _usable(en):
        return (vi if _usable(vi) else ""), (en if _usable(en) else "")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "", ""
    if isinstance(payload, dict):
        return str(payload.get("description_vi") or "").strip(), str(
            payload.get("description_en") or ""
        ).strip()
    return "", ""

def _normalize_source_kind(raw: str | None) -> str:
    kind = (raw or "unknown").strip().lower()
    return kind if kind in SOURCE_KINDS else "unknown"

def _structured_finds(ctx: dict) -> str:
    bits: list[str] = []
    obj = (ctx.get("survey_object") or "").strip()
    if obj:
        bits.append(obj)
    n = 0
    for inst in (ctx.get("instances") or [])[:6]:
        if not isinstance(inst, dict):
            continue
        n += 1
        level = inst.get("level") or ""
        axis = inst.get("axis") or ""
        label = "surface_crack"
        if level:
            label += f"/{level}"
        if axis:
            label += f"/{axis}"
        bits.append(label)
    if not n and ctx.get("has_crack"):
        bits.append("surface_crack")
    return ", ".join(bits) if bits else "none extracted"

def _caption_prompt(ctx: dict) -> str:
    source_kind = _normalize_source_kind(ctx.get("source_kind"))
    seen = _structured_finds(ctx)
    prompt = (
        f"Source kind: {source_kind}. Structured finds: {seen}.\n"
        "Write 2-4 Vietnamese sentences, then 2-4 English sentences.\n"
        "Say: viewpoint (dashcam/survey), pavement type, surroundings, "
        "whether signs/markings/damage are visible, vehicle hood if in frame.\n"
        "If a place name is printed on the photo HUD, you may name that road. "
        "Do not copy HUD lat/lon as GPS facts.\n"
    )
    if ctx.get("real_detection") or (ctx.get("instances") or []) or ctx.get("has_crack"):
        prompt += (
            "If cracks or surface damage are truly visible, add at most one short sentence "
            "in each language about how they look (direction/density in plain words). "
            "Do not list crack ids, scores, mm, or cm.\n"
        )
    else:
        prompt += (
            "If no crack/damage is visible, say the surface looks intact — do not invent cracks.\n"
        )
    prompt += (
        "Reply JSON only:\n"
        '{"description_vi":"mo ta tieng Viet","description_en":"English description"}'
    )
    return prompt

def fallback_caption(ctx: dict) -> tuple[str, str]:
    source_kind = _normalize_source_kind(ctx.get("source_kind"))
    finds = _structured_finds(ctx)
    has_gps = ctx.get("lat") is not None and ctx.get("lon") is not None
    if finds != "none extracted":
        vi = f"Ảnh {source_kind}. VLM ghi nhận: {finds}."
        en = f"{source_kind} image. VLM recorded: {finds}."
    else:
        vi = f"Ảnh {source_kind}. VLM không ghi nhận đối tượng đường có cấu trúc."
        en = f"{source_kind} image. VLM recorded no structured road objects."
    if not has_gps:
        vi += " Không có GPS trong EXIF."
        en += " No GPS in EXIF."
    return vi, en

def describe_scene_caption(ctx: dict) -> tuple[str, str]:
    path = Path(ctx.get("image_path") or "")
    if not path.is_file():
        return fallback_caption(ctx)
    prompt = _caption_prompt(ctx)

    def _call(*, think: bool, num_predict: int) -> tuple[str, str]:
        try:
            raw = chat_vision(
                prompt,
                [path],
                system=CAPTION_SYSTEM,
                think=think,
                num_predict=num_predict,
                fallback_short=False,
                extract=False,
                json_format=False,
            )
        except Exception:
            raw = ""
        return parse_caption(raw or "")

    vi, en = _call(think=False, num_predict=800)
    if not vi and not en:
        vi, en = _call(think=True, num_predict=1800)
    if not vi and not en:
        return fallback_caption(ctx)

    if vi:
        gated = gate_vl_text(vi, ctx)
        vi = gated if _usable(gated) else vi
    if en:
        gated = gate_vl_text(en, ctx)
        en = gated if _usable(gated) else en
    if not _usable(vi) and not _usable(en):
        return fallback_caption(ctx)
    return vi, en
