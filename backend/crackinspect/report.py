from __future__ import annotations

import re
import unicodedata

from .grade import grade_from_ratio
from .ollama_client import extract_vietnamese
from .summarize import _exif_line, _position, build_review, format_detail_from_instances

def _row_grade(rec: dict) -> tuple[int, str, str]:
    detected = bool(rec.get("real_detection"))
    ratio = float(rec.get("crack_ratio") or 0)
    return grade_from_ratio(ratio, detected)

def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text)).strip()

def _too_similar(a: str, b: str) -> bool:
    fa, fb = _fold(a), _fold(b)
    if not fa or not fb:
        return False
    if fa == fb or fa in fb or fb in fa:
        return True
    ta, tb = set(fa.split()), set(fb.split())
    return bool(ta and tb) and len(ta & tb) / min(len(ta), len(tb)) >= 0.72

def scene_text(rec: dict) -> str:
    narrative = (rec.get("description_vi") or "").strip()
    if len(narrative) > 20:
        return narrative
    raw = (rec.get("vl_summary") or "").strip()
    if (
        not raw
        and rec.get("instances")
        and (rec.get("real_detection") or rec.get("has_crack") or rec.get("instances"))
    ):
        return format_detail_from_instances(rec)
    if not raw:
        return ""
    if raw.lower().startswith("supervisor ("):
        if rec.get("instances"):
            return format_detail_from_instances(rec)
        return raw
    raw = extract_vietnamese(raw) or raw
    raw = re.sub(
        r"(?:\d+[\.\)]\s*)?Mức độ theo số đo.*$",
        "",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    raw = re.sub(r"Câu\s*\d+\s*:\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(
        r"\d+[\.\)]\s*(hình dạng|vị trí|mức độ|hiện trường)[^:]*:\s*",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    raw = re.sub(r"bbox=\([^)]+\)(?:-\([^)]+\))?", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r",?\s*vị trí bbox[^.]*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"là\s*,\s*", "là ", raw)
    raw = re.sub(r"\s{2,}", " ", raw).strip(" ,.;")
    kept: list[str] = []
    for sent in re.split(r"(?<=[.!?])\s+", raw):
        s = sent.strip(" ,;")
        if not s or len(s) < 8:
            continue
        if re.search(r"vị\s*trí", s, re.IGNORECASE):
            continue
        if any(_too_similar(s, prev) for prev in kept):
            continue
        kept.append(s[0].upper() + s[1:] if len(s) > 1 else s.upper())
    return " ".join(kept)

def format_problem(records: list[dict]) -> str:
    n = len(records)
    cracked = [r for r in records if r.get("real_detection")]
    k = len(cracked)
    geo = [r for r in records if r.get("lat") is not None]
    geo_txt = (
        f" {len(geo)}/{n} ảnh có GPS (CSV/EXIF)."
        if geo
        else " Không ảnh nào khớp GPS trong bộ annotated."
    )
    mm = [r for r in records if r.get("length_mm") is not None]
    mm_txt = f" {len(mm)}/{n} ảnh có dài/rộng mm (CSV/EXIF)." if mm else ""
    if not cracked:
        return (
            f"Đã kiểm tra {n} ảnh. Model không phát hiện vết nứt rõ trên ảnh nào."
            f"{geo_txt} Đề xuất: không cần xử lý nứt."
        )
    ranked = sorted(cracked, key=lambda r: float(r.get("crack_ratio") or 0), reverse=True)
    top = ranked[0]
    _, top_grade, top_act = _row_grade(top)
    pos = _position(top)
    pos_txt = f", {pos}" if pos else ""
    size_txt = ""
    if top.get("length_mm") is not None:
        size_txt = f", dài {float(top['length_mm']):.1f} mm"
        if top.get("width_avg_mm") is not None:
            size_txt += f", rộng TB {float(top['width_avg_mm']):.2f} mm"
    gps_txt = ""
    if top.get("lat") is not None:
        gps_txt = f", GPS {float(top['lat']):.6f},{float(top['lon']):.6f}"
    return (
        f"Đã kiểm tra {n} ảnh: {k} ảnh có vết nứt, {n - k} ảnh không phát hiện rõ."
        f"{geo_txt}{mm_txt} "
        f"Nặng nhất theo tỷ lệ pixel là {top_grade} tại ảnh {top.get('upload_index')} "
        f"({top.get('image_name')}, {float(top.get('crack_ratio') or 0):.2%}{pos_txt}{size_txt}{gps_txt}). "
        f"Đề xuất chung: {top_act}. "
        "Cấp pixel là quy ước nội bộ (không phải TCVN). mm và GPS lấy từ CSV + EXIF bộ annotated, không bịa."
    )

def format_template_report(records: list[dict]) -> str:
    lines = [
        "## Vấn đề",
        format_problem(records),
        "",
        "## Hiện trường và vết nứt",
    ]
    for rec in records:
        idx = rec.get("upload_index", "?")
        _, grade_txt, action = _row_grade(rec)
        ratio = float(rec.get("crack_ratio") or 0)
        pos = _position(rec)
        scene = scene_text(rec)
        det = rec.get("detector") or "conglomerate"
        det_txt = "LCW (ảnh hiện trường)" if str(det).startswith("lcw") else "Conglomerate (ảnh gần)"
        lines.append(f"**Ảnh {idx} — {rec.get('image_name')}**")
        if rec.get("real_detection"):
            lines.append(scene or "Có vết nứt trên ảnh; chưa có mô tả hiện trường từ VLM.")
            extra = f" Vị trí trong khung: {pos}." if pos else ""
            lines.append(
                f"Số đo: {grade_txt} ({ratio:.2%}, {det_txt}).{extra} Đề xuất: {action}."
            )
            if rec.get("overlay_kind") == "tpfpfn" and rec.get("overlay_recall") is not None:
                lines.append(
                    f"Đối chiếu nhãn (ô 4): recall {float(rec['overlay_recall']):.2f}, "
                    f"precision {float(rec.get('overlay_precision') or 0):.2f}, "
                    f"F1 {float(rec.get('overlay_f1') or 0):.2f}, "
                    f"IoU {float(rec.get('overlay_iou') or 0):.2f} "
                    f"(TP {rec.get('overlay_tp')}, FP {rec.get('overlay_fp')}, FN {rec.get('overlay_fn')})."
                )
                if rec.get("overlay_quality"):
                    lines.append(str(rec["overlay_quality"]))
            lines.append(_exif_line(rec))
        else:
            lines.append(
                f"Không thấy nứt rõ ({ratio:.2%}, {det_txt}). Đề xuất: {action}."
            )
            lines.append(_exif_line(rec))
        lines.append("")
    return "\n".join(lines).rstrip()

def preview_path(rec: dict) -> str:
    from pathlib import Path

    for key in ("overlay_path", "boxes_path", "image_path"):
        p = rec.get(key)
        if p and Path(p).exists():
            return p
    return rec.get("image_path") or ""
