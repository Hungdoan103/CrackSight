from __future__ import annotations

import re
from pathlib import Path

from ..core.config import CRACK_THRESHOLD, DESCRIBE_MIN_PIXELS, DESCRIBE_MIN_RATIO
from .ollamaClient import _strip_think, chat, chat_vision, extract_vietnamese

_HALLUCINATION_RE = re.compile(
    r"(sụp\s*đổ|thảm\s*họa|độ\s*bền|khe nứt sâu|bong\s*tróc|phai\s*màu|sập\b)",
    re.IGNORECASE,
)
_DETAIL_RE = re.compile(
    r"(?m)^\s*[123][\.\)]\s+|Tổng quan vị trí|Phân tích chi tiết|Đánh giá sơ bộ",
    re.IGNORECASE,
)
_CM_RE = re.compile(r"\d+(?:[.,]\d+)?\s*cm\b", re.IGNORECASE)
_MM_RE = re.compile(r"\d+(?:[.,]\d+)?\s*mm\b", re.IGNORECASE)
_GPS_CLAIM_RE = re.compile(
    r"(GPS|tọa\s*độ|Australia|Darwin|latitude|longitude|"
    r"[-+]?\d{1,2}\.\d{3,}\s*,\s*[-+]?\d{1,3}\.\d{3,})",
    re.IGNORECASE,
)

def is_real_detection(ctx: dict) -> bool:
    rec = ctx.get("overlay_recall")
    if ctx.get("overlay_kind") == "tpfpfn" and rec is not None:
        return float(rec) > 0
    ratio = float(ctx.get("crack_ratio") or 0)
    pixels = int(ctx.get("crack_pixels") or 0)
    return ratio >= DESCRIBE_MIN_RATIO and pixels >= DESCRIBE_MIN_PIXELS

def _severity(ratio: float) -> str:
    if ratio < 0.02:
        return "rất ít"
    if ratio < 0.05:
        return "ít"
    if ratio < 0.10:
        return "trung bình"
    return "nhiều"

def _position(ctx: dict) -> str | None:
    bbox = ctx.get("bbox")
    w = float(ctx.get("width") or 0) or 1.0
    h = float(ctx.get("height") or 0) or 1.0
    if not bbox:
        return None
    cx = (bbox["x1"] + bbox["x2"]) / 2 / w
    cy = (bbox["y1"] + bbox["y2"]) / 2 / h
    horiz = "bên trái" if cx < 0.33 else "bên phải" if cx > 0.67 else "giữa theo chiều ngang"
    vert = "phía trên" if cy < 0.33 else "phía dưới" if cy > 0.67 else "giữa theo chiều dọc"
    if 0.33 <= cx <= 0.67 and 0.33 <= cy <= 0.67:
        return "ở giữa ảnh"
    return f"{vert}, {horiz}"

def summarize_fast(ctx: dict) -> str:
    name = ctx.get("image_name") or "ảnh"
    w = ctx.get("width")
    h = ctx.get("height")
    ratio = float(ctx.get("crack_ratio") or 0)
    size = f"{w}x{h}" if w and h else ""
    det = ctx.get("detector") or "conglomerate"
    det_txt = "LCW (ảnh hiện trường)" if str(det).startswith("lcw") else "Conglomerate (ảnh gần)"
    if not is_real_detection(ctx):
        rec = ctx.get("overlay_recall")
        prec = ctx.get("overlay_precision")
        extra = ""
        if ctx.get("overlay_kind") == "tpfpfn" and rec is not None and prec is not None:
            extra = f", ô 4 rec={float(rec):.2f} prec={float(prec):.2f} nên không tính là phát hiện"
        return (
            f"Ảnh {name} ({size}): không thấy nứt rõ "
            f"(tỷ lệ {ratio:.2%}, đo bằng {det_txt}{extra}). Không mô tả VLM."
        )
    pos = _position(ctx)
    pos_txt = f" Vị trí tương đối: {pos}." if pos else ""
    px = ctx.get("crack_pixels")
    px_txt = f", {px} pixel" if px is not None else ""
    quality = (ctx.get("overlay_quality") or "").strip()
    metric_txt = ""
    if ctx.get("overlay_kind") == "tpfpfn" and ctx.get("overlay_recall") is not None:
        metric_txt = (
            f" Ô 4: rec={float(ctx['overlay_recall']):.2f} "
            f"prec={float(ctx.get('overlay_precision') or 0):.2f} "
            f"F1={float(ctx.get('overlay_f1') or 0):.2f} "
            f"IoU={float(ctx.get('overlay_iou') or 0):.2f}."
        )
        if quality:
            metric_txt += f" {quality}"
    return (
        f"Ảnh {name} ({size}): có nứt, mức độ {_severity(ratio)} "
        f"({ratio:.2%}{px_txt}, đo bằng {det_txt}).{pos_txt}{metric_txt}"
    )

def _exif_line(rec: dict) -> str:
    bits = []
    if rec.get("device"):
        bits.append(f"máy {rec['device']}")
    if rec.get("lat") is not None and rec.get("lon") is not None:
        bits.append(f"GPS {float(rec['lat']):.6f},{float(rec['lon']):.6f}")
    if rec.get("length_mm") is not None:
        bits.append(f"dài {float(rec['length_mm']):.1f} mm")
    if rec.get("width_avg_mm") is not None:
        bits.append(f"rộng TB {float(rec['width_avg_mm']):.2f} mm")
    if rec.get("width_max_mm") is not None:
        bits.append(f"rộng max {float(rec['width_max_mm']):.2f} mm")
    if rec.get("gsd_mm_per_px") is not None:
        bits.append(f"GSD {float(rec['gsd_mm_per_px']):.2f} mm/px")
    if rec.get("csv_dataset"):
        bits.append(f"nguồn {rec['csv_dataset']}")
    if not bits:
        return "Metadata: không khớp CSV/EXIF bộ annotated."
    src = rec.get("exif_source") or "csv+exif"
    return f"Metadata ({src}): " + "; ".join(bits) + "."

def context_to_prompt(ctx: dict) -> str:
    bbox = ctx.get("bbox")
    bbox_txt = (
        f"bbox=({bbox['x1']},{bbox['y1']})-({bbox['x2']},{bbox['y2']})"
        if bbox
        else "bbox=none"
    )
    return f"""Bạn là trợ lý kiểm định kết cấu. Chỉ dùng số liệu dưới đây, không bịa chi tiết không có trong context.

Ảnh: {ctx.get("image_name")}
Model đo: {ctx.get("detector") or "conglomerate"}
Kích thước: {ctx.get("width")}x{ctx.get("height")}
crack_ratio: {ctx.get("crack_ratio"):.4%}
crack_pixels: {ctx.get("crack_pixels")}
has_crack: {ctx.get("has_crack")}
{bbox_txt}

Viết summary tiếng Việt 3-5 câu: có nứt hay không, mức độ (rất ít/trung bình/nhiều dựa trên crack_ratio), vị trí tương đối nếu có bbox (trái/phải/trên/dưới/giữa).
Nếu crack_ratio < {CRACK_THRESHOLD:.3%} thì nói không thấy nứt rõ.
Không dùng bullet. Chỉ trả về summary."""

def _strip_hallucinations(text: str) -> str:
    kept = []
    for part in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        if part and not _HALLUCINATION_RE.search(part):
            kept.append(part)
    return " ".join(kept).strip()

def gate_vl_text(text: str, rec: dict) -> str:
    text = _strip_hallucinations(text)
    kept = []
    has_mm = rec.get("length_mm") is not None or rec.get("width_avg_mm") is not None
    has_gps = rec.get("lat") is not None
    for part in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        if not part:
            continue
        if _CM_RE.search(part):
            continue
        if _MM_RE.search(part) and not has_mm:
            continue
        if _GPS_CLAIM_RE.search(part) and not has_gps:
            continue
        kept.append(part)
    return " ".join(kept).strip()

def _zone(box: dict, w: float, h: float) -> str:
    if not box or w <= 0 or h <= 0:
        return "không rõ"
    cx = (float(box.get("x1", 0)) + float(box.get("x2", 0))) / 2 / w
    cy = (float(box.get("y1", 0)) + float(box.get("y2", 0))) / 2 / h
    horiz = "trái" if cx < 0.33 else "phải" if cx > 0.67 else "giữa"
    vert = "trên" if cy < 0.33 else "dưới" if cy > 0.67 else "giữa"
    if horiz == "giữa" and vert == "giữa":
        return "giữa ảnh"
    return f"{vert}-{horiz}"

def _worst_instance(items: list[dict]) -> dict | None:
    if not items:
        return None
    return max(
        items,
        key=lambda row: (
            2 if row.get("level") == "cao" else 1 if row.get("level") == "trung bình" else 0,
            float(row.get("score") or 0),
            float(row.get("pixels") or 0),
        ),
    )

def _axis_label(axis: str | None) -> str:
    raw = (axis or "").strip().lower()
    if raw.startswith("ngang"):
        return "Phương ngang"
    if raw.startswith("dọc") or raw.startswith("doc"):
        return "Phương dọc"
    return "Chưa rõ hướng"

def _fmt_measure(mm: float | None, px: float | None, as_length: bool) -> str:
    if mm is not None:
        if as_length and mm >= 10:
            return f"{mm / 10:.1f} cm"
        return f"{mm:.2f} mm"
    if px is not None:
        return f"{px:.0f} px (chưa có tỷ lệ mm)"
    return "chưa đo"

def _risk_text(level: str) -> str:
    if level == "cao":
        return "Ảnh hưởng đến kết cấu, mức độ nguy hiểm cao"
    if level == "trung bình":
        return "Ảnh hưởng cục bộ, mức độ nguy hiểm trung bình"
    return "Chưa có dấu hiệu nguy hiểm ngay, mức độ nhẹ"

def build_review(ctx: dict) -> dict:
    items = [i for i in (ctx.get("instances") or []) if isinstance(i, dict)]
    lcw = ctx.get("scene_kind") == "hientruong" or str(ctx.get("detector") or "").startswith("lcw")
    obj = (ctx.get("survey_object") or "").strip()
    if not obj:
        obj = "Cột / bệ bê tông (ảnh hiện trường)" if lcw else "Bề mặt bê tông (ảnh cận)"
    n = len(items)
    if n == 0:
        return {
            "object": obj,
            "count": 0,
            "count_text": "Phát hiện tổng cộng 0 vết nứt.",
            "focus": None,
            "others": "Không có vết nứt phụ.",
            "actions": [
                "Theo dõi định kỳ",
                "Đánh giá kết cấu tổng thể nếu xuất hiện vết mới",
            ],
        }
    worst = _worst_instance(items) or items[0]
    gsd = ctx.get("gsd_mm_per_px")
    length_mm = worst.get("length_mm")
    width_mm = worst.get("width_avg_mm")
    if length_mm is None and gsd and worst.get("length_px") is not None:
        length_mm = float(worst["length_px"]) * float(gsd)
    if width_mm is None and gsd and worst.get("width_avg_px") is not None:
        width_mm = float(worst["width_avg_px"]) * float(gsd)
    level = worst.get("level") or "nhẹ"
    wid = int(worst.get("id") or 1)
    rest = [i for i in items if int(i.get("id") or 0) != wid]
    n_high = sum(1 for i in rest if i.get("level") == "cao")
    n_mid = sum(1 for i in rest if i.get("level") == "trung bình")
    n_low = len(rest) - n_high - n_mid
    if rest:
        others = (
            f"Vết nứt #{', #'.join(str(i.get('id')) for i in rest[:8])}"
            f"{'…' if len(rest) > 8 else ''}: "
            f"{n_high} cao, {n_mid} trung bình, {n_low} nhẹ — "
            "mức độ hiện tại chủ yếu trung bình/nhẹ, chưa có dấu hiệu nguy hiểm ngay."
        )
    else:
        others = "Không có vết nứt phụ."
    actions = [
        f"Kiểm tra chi tiết — vết nứt #{wid}",
        f"Theo dõi định kỳ — {len(rest)} vết còn lại" if rest else "Theo dõi định kỳ",
        "Xử lý chống thấm — chỉ khi có dấu hiệu ẩm/thấm",
        "Đánh giá kết cấu tổng thể",
    ]
    return {
        "object": obj,
        "count": n,
        "count_text": f"Phát hiện tổng cộng {n} vết nứt.",
        "focus": {
            "id": wid,
            "length": _fmt_measure(
                None if length_mm is None else float(length_mm),
                None if worst.get("length_px") is None else float(worst["length_px"]),
                True,
            ),
            "width": _fmt_measure(
                None if width_mm is None else float(width_mm),
                None if worst.get("width_avg_px") is None else float(worst["width_avg_px"]),
                False,
            ),
            "axis": _axis_label(str(worst.get("axis") or "")),
            "risk": _risk_text(level),
            "level": level,
        },
        "others": others,
        "actions": actions,
    }

def format_detail_from_instances(ctx: dict) -> str:
    rev = build_review(ctx)
    focus = rev.get("focus") or {}
    lines = [
        f"Đối tượng khảo sát / Vị trí: {rev['object']}",
        f"Tổng quan số lượng: {rev['count_text']}",
    ]
    if focus:
        lines.extend(
            [
                f"Chi tiết từng vết nứt trọng điểm (Vết nứt #{focus['id']}):",
                f"- Kích thước ước tính: Chiều dài {focus['length']}; Chiều rộng {focus['width']}.",
                f"- Đặc điểm hình học / Hướng phát triển: {focus['axis']}.",
                f"- Đánh giá mức độ ảnh hưởng / Rủi ro: {focus['risk']}.",
            ]
        )
    lines.append(f"Nhận định tình trạng chung cho các vết nứt phụ: {rev['others']}")
    lines.append("Hành động đề xuất / Khuyến nghị:")
    lines.extend(f"- {act}" for act in rev["actions"])
    return "\n".join(lines)

def describe_vl(ctx: dict, stats: str) -> str:
    path = ctx.get("image_path")
    prompt = (
        "Nhìn đúng vật thể trên ảnh. Trả lời một cụm tiếng Việt, tối đa 8 chữ, "
        "gồm loại cấu kiện và vị trí nếu thấy (cột, tường, dầm, bản mặt cầu, mặt đường, trong nhà, ngoài trời). "
        "Phải khớp ảnh, không chép mẫu. Cấm tiếng Anh, cấm giải thích, cấm mm/cm/GPS."
    )
    try:
        raw = chat_vision(prompt, [path], think=False, num_predict=80, fallback_short=False)
        obj = gate_vl_text(raw, ctx)
        obj = re.sub(r"\s+", " ", obj).strip(" .")
        if obj and len(obj) <= 48 and not re.search(r"[A-Za-z]{4,}", obj):
            ctx["survey_object"] = obj
    except Exception:
        pass
    return format_detail_from_instances(ctx)

def _instance_measures(inst: dict, rec: dict) -> dict:
    gsd = rec.get("gsd_mm_per_px")
    length_mm = inst.get("length_mm")
    width_mm = inst.get("width_avg_mm") or inst.get("width_mm")
    if length_mm is None and gsd and inst.get("length_px") is not None:
        length_mm = float(inst["length_px"]) * float(gsd)
    if width_mm is None and gsd and inst.get("width_avg_px") is not None:
        width_mm = float(inst["width_avg_px"]) * float(gsd)
    src_w = float(rec.get("image_w") or rec.get("width") or 0)
    src_h = float(rec.get("image_h") or rec.get("height") or 0)
    return {
        "length": _fmt_measure(
            None if length_mm is None else float(length_mm),
            None if inst.get("length_px") is None else float(inst["length_px"]),
            True,
        ),
        "width": _fmt_measure(
            None if width_mm is None else float(width_mm),
            None if inst.get("width_avg_px") is None else float(inst["width_avg_px"]),
            False,
        ),
        "risk": _risk_text(str(inst.get("level") or "nhẹ")),
        "axis": _axis_label(str(inst.get("axis") or "")),
        "position": _zone(inst.get("bbox") or {}, src_w, src_h),
    }

_EN_WORD_RE = re.compile(
    r"\b(like|okay|ok|wait|position|shape|detail|surface|object|the|and|for)\b",
    re.IGNORECASE,
)
_GENERIC_POS_RE = re.compile(
    r"(trên\s+bề\s+mặt(\s+vật\s+thể)?|bề\s+mặt\s+vật\s+thể|không\s+rõ)",
    re.IGNORECASE,
)
_PROMPT_ECHO_RE = re.compile(
    r"(cấm\s+cụm|cấm\s+tiếng|không\s+số\s+đo|không\s+copy|không\s+lặp|"
    r"đúng\s+2\s+dòng|nhìn\s+crop|không\s+viết\s+mục|crop\s+vết\s+nứt|"
    r"mm\s*/\s*cm|sụp\s+đổ|không\s+copy\s+mẫu|không\s+tiêu\s+đề|không\s+liệt\s+kê|"
    r"thẳng,\s*cong,\s*mạng|\(\s*thẳng|đang\s+thấy\s+trên\s+ảnh|"
    r"có\s+cong\s+không|hay\s+phân\s+nhánh|có\s+mạng\s+lưới\s+không|"
    r"mô\s+tả\s+đúng\s+hình\s+dạng|không\s+đánh\s+số)",
    re.IGNORECASE,
)

def _clean_vi_phrase(text: str) -> str:
    text = _EN_WORD_RE.sub(" ", text or "")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = text.strip(" .,;:-")
    if re.search(r"[A-Za-z]{5,}", text):
        return ""
    return text

def _is_prompt_echo(text: str) -> bool:
    return bool(_PROMPT_ECHO_RE.search(text or ""))

def _fallback_detail(inst_id: int, facts: dict) -> str:
    axis = str(facts.get("axis") or "").replace("Phương ", "").lower()
    if axis == "ngang":
        shape = "chạy ngang, một dải trên bề mặt bê tông"
    elif axis == "dọc":
        shape = "chạy dọc, một dải trên bề mặt bê tông"
    else:
        shape = "thấy rõ trên bề mặt bê tông"
    return f"Vết nứt #{inst_id} {shape}."

def _unique_sentences(text: str, limit: int = 2) -> str:
    parts = [re.sub(r"\s+", " ", p).strip(" .") for p in re.split(r"(?<=[.!?])\s+", text or "") if p.strip()]
    kept: list[str] = []
    seen: set[str] = set()
    for part in parts:
        part = _clean_vi_phrase(part)
        if re.match(r"(?i)^vị\s*trí\b", part) or _is_prompt_echo(part):
            continue
        key = re.sub(r"[^\wàáảãạăâèéêìíòóôơùúưỳýđ]", "", part.lower())
        core = re.sub(r"^vếtnứtcóhìnhdạng", "", key)
        if len(key) < 10 or key in seen:
            continue
        if any(key in other or other in key or (core and core[:14] == re.sub(r"^vếtnứtcóhìnhdạng", "", other)[:14]) for other in seen):
            continue
        seen.add(key)
        kept.append(part)
        if len(kept) >= limit:
            break
    return ". ".join(kept) + ("." if kept else "")

def _surface_place(inst: dict, rec: dict) -> str:
    obj = (rec.get("survey_object") or "bề mặt bê tông").strip().rstrip(".")
    obj = re.sub(r"^(ảnh cận|vết nứt)\s+", "", obj, flags=re.I)
    zone = _zone(inst.get("bbox") or {}, float(rec.get("image_w") or rec.get("width") or 0), float(rec.get("image_h") or rec.get("height") or 0))
    axis = _axis_label(str(inst.get("axis") or "")).replace("Phương ", "").lower()
    if zone == "giữa ảnh":
        place = f"ở giữa {obj}"
    else:
        place = f"phía {zone.replace('-', ' ')} của {obj}"
    if axis in {"ngang", "dọc"}:
        return f"{place}, vết chạy theo phương {axis}"
    return place

def _is_specific_position(text: str) -> bool:
    text = _clean_vi_phrase(text)
    if len(text) < 8 or _GENERIC_POS_RE.fullmatch(text) or _GENERIC_POS_RE.search(text) and len(text) < 28:
        return False
    return bool(re.search(r"(trên|dưới|trái|phải|giữa|mép|góc|cột|tường|dầm|mặt)", text, re.I))

def _parse_closeup_vl(raw: str) -> tuple[str, str]:
    text = gate_vl_text(_strip_think(raw or ""), {})
    text = re.sub(r"\r", "", text)
    blob = re.sub(r"\n+", " ", text)
    detail_m = re.search(r"(chi\s*tiết|mô\s*tả(?:\s*chi\s*tiết)?)\s*:\s*(.+?)(?=vị\s*trí\s*:|$)", blob, re.I | re.S)
    pos_m = re.search(r"vị\s*trí(?:\s+trên\s+bề\s+mặt)?\s*:\s*(.+)$", blob, re.I | re.S)
    detail = _unique_sentences(_clean_vi_phrase(detail_m.group(2) if detail_m else ""), 2)
    position = _clean_vi_phrase(pos_m.group(1) if pos_m else "")
    if _is_prompt_echo(detail):
        detail = ""
    if _is_prompt_echo(position):
        position = ""
    if not detail:
        leftover = blob
        leftover = re.sub(r"vị\s*trí(?:\s+trên\s+bề\s+mặt)?\s*:.*$", "", leftover, flags=re.I)
        leftover = re.sub(r"(chi\s*tiết|mô\s*tả)\s*:", "", leftover, flags=re.I)
        if not _is_prompt_echo(leftover):
            detail = _unique_sentences(extract_vietnamese(leftover) or leftover, 2)
    return detail, position

def format_closeup(fields: dict) -> str:
    return "\n".join(
        [
            f"Mô tả chi tiết: {fields.get('detail') or 'Chưa có mô tả.'}",
            f"Chiều dài: {fields.get('length') or 'chưa đo'}",
            f"Chiều rộng: {fields.get('width') or 'chưa đo'}",
            f"Mức ảnh hưởng: {fields.get('risk') or 'chưa đánh giá'}",
            f"Vị trí trên bề mặt: {fields.get('position') or 'không rõ'}",
        ]
    )

def describe_closeup(crop_path: str | Path, inst_id: int, rec: dict | None = None) -> dict:
    rec = rec or {}
    inst = next((i for i in rec.get("instances") or [] if int(i.get("id", -1)) == inst_id), {}) or {}
    facts = _instance_measures(inst, rec)
    position = _surface_place(inst, rec)
    detail = ""
    prompt = (
        f"Ảnh cận vết nứt #{inst_id}. "
        "Viết đúng 2 câu tiếng Việt. Câu 1 hiện trường bề mặt. Câu 2 hình dạng vết. "
        "Không giải thích."
    )
    try:
        raw = chat_vision(
            prompt,
            [crop_path],
            think=False,
            num_predict=220,
            fallback_short=False,
            keep_alive="0",
        )
        text = extract_vietnamese(raw) or gate_vl_text(_strip_think(raw or ""), rec)
        detail = _unique_sentences(text, 2)
        if _is_prompt_echo(detail):
            detail = ""
    except Exception:
        pass
    if not detail:
        detail = _fallback_detail(inst_id, facts)
    fields = {
        "id": inst_id,
        "detail": detail,
        "length": facts["length"],
        "width": facts["width"],
        "risk": facts["risk"],
        "position": position,
        "axis": facts["axis"],
    }
    fields["text"] = format_closeup(fields)
    return fields

def _parse_question(question: str) -> dict:
    q = (question or "").lower()
    ids = [int(n) for n in re.findall(r"#\s*(\d+)", q)]
    ids += [int(n) for n in re.findall(r"vết(?:\s*nứt)?\s+(\d+)\b", q)]
    ids = sorted(set(ids))
    levels: list[str] = []
    if re.search(r"\bnhẹ\b|nhe\b", q):
        levels.append("nhẹ")
    if re.search(r"trung\s*bình|trung\s*binh", q):
        levels.append("trung bình")
    if re.search(r"\bcao\b|nguy\s*hiểm|nghiem\s*trong|nghiêm\s*trọng", q):
        levels.append("cao")
    topic = "chung"
    if re.search(r"miêu\s*tả|mô\s*tả|hình\s*dạng|trông|nhận\s*xét", q):
        topic = "mota"
    elif re.search(r"làm\s*gì|đề\s*xuất|hành\s*động|nên\s+làm|xử\s*lý", q):
        topic = "hanhdong"
    elif re.search(r"dài|rộng|kích\s*thước|px|mm", q):
        topic = "kichthuoc"
    elif re.search(r"hướng|ngang|dọc", q):
        topic = "huong"
    elif re.search(r"vị\s*trí|ở\s*đâu|chỗ\s+nào", q):
        topic = "vitri"
    elif re.search(r"ưu\s*tiên|nặng\s*nhất|nguy\s*hiểm\s*nhất", q):
        topic = "uutien"
    if re.search(r"tại\s*sao|vì\s*sao|vì\s*đâu|đánh\s*giá\s+là|xếp\s+mức", q):
        topic = "lydo"
    elif re.search(r"như\s*thế\s*nào", q):
        topic = "lydo" if ("cao" in levels or "mức" in q) else "mota"
    elif re.search(r"hiện\s*trường\s+gì|đối\s*tượng|là\s+gì|loại\s+(ảnh|hiện|công)", q):
        topic = "doituong"
    elif re.search(r"hiện\s*trường\s+nào|ảnh\s+nào|bức\s+nào|file\s+nào|phiên|toàn\s+bộ|hệ\s+thống", q):
        topic = "anhnao"
    return {"ids": ids, "levels": levels, "topic": topic}

def _all_instances(rec: dict) -> list[dict]:
    return [i for i in (rec.get("instances") or []) if isinstance(i, dict)]

def _pick_instances(rec: dict, scope: dict, inspect_id: int | None) -> list[dict]:
    items = _all_instances(rec)
    if scope["ids"]:
        picked = [i for i in items if int(i.get("id") or 0) in scope["ids"]]
        if picked:
            return picked
    if scope["levels"]:
        picked = [i for i in items if (i.get("level") or "nhẹ") in scope["levels"]]
        if picked:
            return picked
    if inspect_id is not None and scope["topic"] != "chung":
        picked = [i for i in items if int(i.get("id") or 0) == inspect_id]
        if picked:
            return picked
    return items

def _scope_label(scope: dict, picked: list[dict]) -> str:
    if scope["ids"]:
        return "các vết " + ", ".join(f"#{i}" for i in scope["ids"])
    if scope["levels"]:
        return "các vết mức " + ", ".join(scope["levels"])
    if scope.get("topic") == "anhnao":
        return "các hiện trường trong phiên"
    return f"{len(picked)} vết trong phiên"

def _chat_facts(
    rec: dict,
    inspect_id: int | None = None,
    picked: list[dict] | None = None,
    scope: dict | None = None,
) -> str:
    review = build_review(rec)
    items = picked if picked is not None else _all_instances(rec)
    lines = [
        f"Ảnh: {rec.get('image_name')}",
        f"Đối tượng khảo sát: {review.get('object')}",
        f"Tổng ảnh: {review.get('count_text')}",
        f"Phạm vi câu hỏi: {_scope_label(scope or {}, items)} — {len(items)} vết.",
    ]
    has_mm = rec.get("length_mm") is not None or rec.get("gsd_mm_per_px") is not None
    if not has_mm:
        lines.append("Chưa có tỷ lệ mm. Không được bịa cm/mm.")
    if rec.get("lat") is None:
        lines.append("Không có GPS.")
    src_w = float(rec.get("image_w") or rec.get("width") or 0)
    src_h = float(rec.get("image_h") or rec.get("height") or 0)
    for inst in items:
        iid = int(inst.get("id") or 0)
        meas = _instance_measures(inst, rec)
        lines.append(
            f"Vết #{iid}: dài {meas['length']}; rộng {meas['width']}; "
            f"{meas['axis']}; mức {inst.get('level') or 'nhẹ'}; "
            f"vị trí {_zone(inst.get('bbox') or {}, src_w, src_h)}; "
            f"đề xuất {inst.get('action') or 'theo dõi định kỳ'}."
        )
        closeup = inst.get("closeup")
        if isinstance(closeup, dict) and closeup.get("detail"):
            lines.append(f"Mô tả cận #{iid}: {closeup.get('detail')}")
    if inspect_id is not None:
        lines.append(f"Người dùng đang xem phóng to vết #{inspect_id}.")
    return "\n".join(line for line in lines if line)

def _assess_from_detect(rec: dict, picked: list[dict] | None = None, scope: dict | None = None) -> str:
    all_items = _all_instances(rec)
    items = picked if picked is not None else all_items
    if not all_items:
        return "Trên ảnh này DeepInspect không tách được vết nứt nào. Chưa có cơ sở đánh giá."
    if not items:
        return f"Không thấy vết nào khớp phạm vi hỏi ({_scope_label(scope or {}, [])})."
    src_w = float(rec.get("image_w") or rec.get("width") or 0)
    src_h = float(rec.get("image_h") or rec.get("height") or 0)
    ids = [int(i.get("id") or 0) for i in items]
    ngang = [i for i in items if str(i.get("axis") or "").startswith("ngang")]
    doc = [i for i in items if str(i.get("axis") or "").startswith("dọc") or str(i.get("axis") or "").startswith("doc")]
    zones = [_zone(i.get("bbox") or {}, src_w, src_h) for i in items]
    zone_txt = ", ".join(sorted(set(zones))[:4])
    lengths = [float(i.get("length_px") or 0) for i in items if i.get("length_px") is not None]
    widths = [float(i.get("width_avg_px") or 0) for i in items if i.get("width_avg_px") is not None]
    level = (scope or {}).get("levels") or []
    topic = (scope or {}).get("topic") or "chung"
    id_range = ", ".join(f"#{i}" for i in ids[:12]) + ("…" if len(ids) > 12 else "")
    parts = [f"Theo detect, {_scope_label(scope or {}, items)} gồm {len(items)} vết ({id_range})."]
    if topic == "mota" or "nhẹ" in level:
        parts.append(
            f"Nhóm này chủ yếu {'phương ngang' if len(ngang) >= len(doc) else 'phương dọc'} "
            f"({len(ngang)} ngang, {len(doc)} dọc), rải ở {zone_txt}."
        )
        if lengths:
            parts.append(
                f"Chiều dài trên mask khoảng {min(lengths):.0f}–{max(lengths):.0f} px; "
                f"chiều rộng trung bình khoảng {min(widths):.0f}–{max(widths):.0f} px."
                if widths
                else f"Chiều dài trên mask khoảng {min(lengths):.0f}–{max(lengths):.0f} px."
            )
        parts.append(
            "Mức nhẹ theo phân loại detect: ảnh hưởng cục bộ thấp, nên theo dõi định kỳ, "
            "chưa cần ưu tiên như vết mức cao."
        )
    elif topic == "hanhdong":
        acts = sorted({str(i.get("action") or "theo dõi định kỳ") for i in items})
        parts.append("Hành động đề xuất từ detect: " + "; ".join(acts) + ".")
    elif topic == "kichthuoc" and lengths:
        parts.append(
            f"Dài {min(lengths):.0f}–{max(lengths):.0f} px"
            + (f", rộng {min(widths):.0f}–{max(widths):.0f} px." if widths else ".")
            + " Chưa có tỷ lệ mm."
        )
    else:
        high = [int(i.get("id") or 0) for i in all_items if i.get("level") == "cao"]
        parts.append(f"Trong cả ảnh còn {len(high)} vết mức cao." if high else "Không có vết mức cao.")
    if rec.get("length_mm") is None and rec.get("gsd_mm_per_px") is None:
        parts.append("Chưa có tỷ lệ mm nên không quy ra cm.")
    return " ".join(parts)

def _keep_chat_vi(text: str, rec: dict) -> str:
    cleaned = gate_vl_text(_strip_think(extract_vietnamese(text) or text), rec)
    kept: list[str] = []
    for part in re.split(r"(?<=[.!?…])\s+", cleaned or ""):
        line = re.sub(r"\s+", " ", part).strip()
        if not line or re.match(r"(?i)^(okay|wait|so |the |here)", line):
            continue
        if re.search(
            r"(?i)^(bạn là kỹ sư|phiếu|phạm vi câu hỏi|cấm bịa|câu hỏi:|trả lời:|phiên có \d+|ảnh đang mở)",
            line,
        ):
            continue
        if "vết trên mọi ảnh" in line and len(line) < 90:
            continue
        if re.search(r"[àáạảãăâèéêìíòóôơùúưỳýđ]", line, re.I) or re.search(
            r"\b(vết|nứt|mức|ảnh|cột|theo dõi|nguy hiểm)\b", line, re.I
        ):
            kept.append(line)
    return " ".join(kept).strip()

def _flatten_instances(records: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        obj = (rec.get("survey_object") or "").strip() or build_review(rec).get("object")
        for inst in _all_instances(rec):
            row = dict(inst)
            row["_image"] = rec.get("image_name")
            row["_object"] = obj
            row["_rec"] = rec
            rows.append(row)
    return rows

def _mentioned_images(text: str, records: list[dict]) -> list[str]:
    blob = (text or "").lower()
    found: list[str] = []
    for rec in records:
        name = str(rec.get("image_name") or "")
        if not name:
            continue
        stem = Path(name).stem.lower()
        if name.lower() in blob or (stem and re.search(rf"\b{re.escape(stem)}\b", blob)):
            found.append(name)
    return found

def _high_records(records: list[dict]) -> list[dict]:
    return [r for r in records if any(i.get("level") == "cao" for i in _all_instances(r))]

def _hint_images(question: str, history: list[dict] | None, records: list[dict]) -> list[str]:
    hist = " ".join(str(m.get("text") or "") for m in (history or []) if isinstance(m, dict))
    q = (question or "").lower()
    if re.search(r"\b(ấy|này|kia|hai\s+ảnh|2\s+ảnh|2\s+hiện|hai\s+hiện)\b", q):
        hist_names = _mentioned_images(hist, records)
        if hist_names:
            return hist_names
        return [str(r.get("image_name")) for r in _high_records(records) if r.get("image_name")]
    mentioned = _mentioned_images(f"{question} {hist}", records)
    if mentioned and len(mentioned) < len(records):
        return mentioned
    return []

def _level_reason(inst: dict, rec: dict) -> str:
    score = float(inst.get("score") or 0)
    wmm = inst.get("width_avg_mm")
    px = int(inst.get("pixels") or 0)
    sib = [i for i in _all_instances(rec) if int(i.get("id") or 0) != int(inst.get("id") or 0)]
    max_other = max((int(i.get("pixels") or 0) for i in sib), default=0)
    if wmm is not None:
        width = float(wmm)
        if width >= 3:
            return f"rộng {width:.2f} mm ≥ 3 mm nên xếp mức cao"
        if width >= 1.5:
            return f"rộng {width:.2f} mm nên xếp trung bình"
        return f"rộng {width:.2f} mm nên xếp nhẹ"
    if score >= 0.9:
        extra = ", đây là vết chiếm nhiều pixel nhất trên mask" if px >= max_other else ""
        return f"điểm detect {score:.2f} (≥ 0,90){extra}; chưa có tỷ lệ mm"
    if score >= 0.75:
        return f"điểm detect {score:.2f} (0,75–0,89) nên xếp trung bình"
    return f"điểm detect {score:.2f} (< 0,75) nên xếp nhẹ"

def _is_echo(answer: str, question: str) -> bool:
    a = re.sub(r"\s+", " ", re.sub(r"[?.!,;:]+", " ", (answer or "").lower())).strip()
    q = re.sub(r"\s+", " ", re.sub(r"[?.!,;:]+", " ", (question or "").lower())).strip()
    if not a:
        return True
    if q and q in a and len(a) <= len(q) + 48:
        return True
    qtoks = [t for t in q.split() if len(t) > 1]
    atoks = [t for t in a.split() if len(t) > 1]
    if not qtoks:
        return False
    hit = sum(1 for t in qtoks if t in atoks)
    return hit / len(qtoks) >= 0.75 and len(atoks) <= len(qtoks) + 6

def _pick_session(
    records: list[dict],
    scope: dict,
    inspect_id: int | None,
    focus_image: str | None,
    hint_names: list[str] | None = None,
) -> list[dict]:
    rows = _flatten_instances(records)
    if hint_names:
        hinted = [r for r in rows if r.get("_image") in hint_names]
        if hinted:
            rows = hinted
    if scope["ids"] and focus_image:
        picked = [
            r
            for r in rows
            if int(r.get("id") or 0) in scope["ids"] and r.get("_image") == focus_image
        ]
        if picked:
            return picked
    if scope["ids"]:
        picked = [r for r in rows if int(r.get("id") or 0) in scope["ids"]]
        if picked:
            return picked
    if scope["levels"]:
        picked = [r for r in rows if (r.get("level") or "nhẹ") in scope["levels"]]
        if picked:
            return picked
    if inspect_id is not None and focus_image and scope["topic"] not in {"chung", "anhnao"}:
        picked = [
            r
            for r in rows
            if int(r.get("id") or 0) == inspect_id and r.get("_image") == focus_image
        ]
        if picked:
            return picked
    return rows

def _session_facts(
    records: list[dict],
    picked: list[dict],
    scope: dict,
    focus_image: str | None,
    inspect_id: int | None,
) -> str:
    names = [str(r.get("image_name") or "") for r in records if r.get("image_name")]
    lines = [f"Phiên có {len(names)} ảnh: {', '.join(names)}."]
    if focus_image:
        lines.append(f"Ảnh đang mở trên giao diện: {focus_image}.")
    lines.append(f"Phạm vi câu hỏi: {_scope_label(scope, picked)} — {len(picked)} vết trên mọi ảnh.")
    by: dict[str, list[dict]] = {}
    for row in picked:
        by.setdefault(str(row.get("_image") or ""), []).append(row)
    for rec in records:
        name = str(rec.get("image_name") or "")
        review = build_review(rec)
        insts = by.get(name) or []
        all_n = len(_all_instances(rec))
        high_n = sum(1 for i in _all_instances(rec) if i.get("level") == "cao")
        lines.append(
            f"ẢNH {name}: {review.get('object')}; tổng {all_n} vết, {high_n} mức cao; "
            f"khớp câu hỏi: {len(insts)} vết."
        )
        src_w = float(rec.get("image_w") or rec.get("width") or 0)
        src_h = float(rec.get("image_h") or rec.get("height") or 0)
        has_mm = rec.get("length_mm") is not None or rec.get("gsd_mm_per_px") is not None
        if not has_mm:
            lines.append(f"  {name}: chưa có tỷ lệ mm.")
        for inst in insts[:24]:
            meas = _instance_measures(inst, rec)
            iid = int(inst.get("id") or 0)
            lines.append(
                f"  {name} #{iid}: dài {meas['length']}; rộng {meas['width']}; "
                f"{meas['axis']}; mức {inst.get('level') or 'nhẹ'}; "
                f"điểm {float(inst.get('score') or 0):.2f}; {int(inst.get('pixels') or 0)} px; "
                f"lý do mức: {_level_reason(inst, rec)}; "
                f"vị trí {_zone(inst.get('bbox') or {}, src_w, src_h)}."
            )
    if inspect_id is not None and focus_image:
        lines.append(f"Người dùng đang phóng to {focus_image} vết #{inspect_id}.")
    return "\n".join(lines)

def _assess_session(records: list[dict], picked: list[dict], scope: dict) -> str:
    if not records:
        return "Chưa có ảnh nào trong phiên phân tích."
    names = [str(r.get("image_name") or "") for r in records]
    topic = scope.get("topic") or "chung"
    levels = scope.get("levels") or []
    rec_by = {str(r.get("image_name") or ""): r for r in records}
    by: dict[str, list[dict]] = {}
    for row in picked:
        by.setdefault(str(row.get("_image") or ""), []).append(row)
    used = [rec_by[n] for n in by if n in rec_by] or records

    if topic == "doituong":
        parts = []
        for rec in used:
            kind = (
                "ảnh hiện trường (cảnh rộng)"
                if rec.get("scene_kind") == "hientruong"
                else "ảnh cận bề mặt"
            )
            parts.append(
                f"{rec.get('image_name')} là {kind}, đối tượng khảo sát: {build_review(rec).get('object')}."
            )
        return " ".join(parts) or "Chưa rõ đối tượng khảo sát."

    if topic == "lydo" or (topic != "doituong" and "cao" in levels and topic != "anhnao"):
        rows = picked or _flatten_instances(used)
        if levels:
            rows = [r for r in rows if (r.get("level") or "nhẹ") in levels] or rows
        if not rows:
            return "Không có vết khớp để giải thích mức."
        parts = [
            "Mức được xếp từ phiếu detect: nếu chưa có mm thì điểm ≥ 0,90 là cao, "
            "0,75–0,89 trung bình, dưới đó là nhẹ. Điểm tỷ lệ với diện tích mask."
        ]
        for row in rows[:8]:
            rec = row.get("_rec") or rec_by.get(str(row.get("_image") or "")) or {}
            meas = _instance_measures(row, rec)
            parts.append(
                f"Trên {row.get('_image')}, vết #{int(row.get('id') or 0)} mức {row.get('level') or 'nhẹ'}: "
                f"dài {meas['length']}, rộng {meas['width']}, {meas['axis']}. "
                f"{_level_reason(row, rec).rstrip('.').capitalize()}. "
                f"Đề xuất: {row.get('action') or 'theo dõi định kỳ'}."
            )
        return " ".join(parts)

    if topic == "anhnao" or ("cao" in levels and topic == "chung"):
        risky = []
        for rec in records:
            highs = [i for i in _all_instances(rec) if i.get("level") == "cao"]
            if highs:
                ids = ", ".join(f"#{int(i.get('id') or 0)}" for i in highs)
                risky.append(f"{rec.get('image_name')} — {build_review(rec).get('object')} ({ids})")
        if risky:
            text = "Hiện trường có vết mức cao: " + "; ".join(risky) + "."
        else:
            text = "Không ảnh nào có vết mức cao."
        ok = [n for n in names if n and n not in {r.get("image_name") for r in _high_records(records)}]
        if ok:
            text += " Ảnh chưa thấy vết mức cao: " + ", ".join(ok) + "."
        return text

    if not picked:
        return f"Trong {len(names)} ảnh ({', '.join(names)}) không có vết khớp từ khóa."
    parts = []
    for name, insts in by.items():
        rec = rec_by.get(name) or {}
        ids = ", ".join(f"#{int(i.get('id') or 0)}" for i in insts[:8])
        extra = "…" if len(insts) > 8 else ""
        parts.append(
            f"{name} ({build_review(rec).get('object')}): {len(insts)} vết {ids}{extra}."
        )
    return " ".join(parts)

def answer_chat(
    records: list[dict],
    question: str,
    inspect_id: int | None = None,
    focus_image: str | None = None,
    history: list[dict] | None = None,
) -> str:
    q = re.sub(r"\s+", " ", question or "").strip()
    if not q:
        return "Hãy hỏi về vết nứt trong phiên phân tích."
    recs = [r for r in records if isinstance(r, dict)]
    if not recs:
        return "Chưa có ảnh nào trong phiên."
    scope = _parse_question(q)
    hints = _hint_images(q, history, recs)
    picked = _pick_session(recs, scope, inspect_id, focus_image, hints)
    fallback = _assess_session(recs, picked, scope)
    if scope.get("topic") in {"lydo", "doituong", "anhnao"}:
        return fallback
    focus = _scope_label(scope, picked)
    gate_rec = {
        "length_mm": next((r.get("length_mm") for r in recs if r.get("length_mm") is not None), None),
        "width_avg_mm": next((r.get("width_avg_mm") for r in recs if r.get("width_avg_mm") is not None), None),
        "lat": next((r.get("lat") for r in recs if r.get("lat") is not None), None),
        "gsd_mm_per_px": next((r.get("gsd_mm_per_px") for r in recs if r.get("gsd_mm_per_px") is not None), None),
    }
    prior = ""
    for msg in (history or [])[-6]:
        if not isinstance(msg, dict):
            continue
        role = "Kỹ sư" if msg.get("role") == "user" else "Trợ lý"
        prior += f"{role}: {msg.get('text') or ''}\n"
    prompt = (
        "Bạn là kỹ sư đánh giá vết nứt trên nhiều ảnh của cả phiên. Chỉ tiếng Việt, 3 đến 8 câu. "
        f"Trả lời ĐÚNG câu hỏi về {focus}. Không lặp lại câu hỏi. "
        "Khi nói 'ấy/này/2 ảnh' thì dùng các ảnh vừa nêu trong hội thoại. "
        "Nêu tên file. Được phép nhận xét định tính dựa trên phiếu detect. "
        "Cấm bịa mm/cm/GPS nếu phiếu chưa có tỷ lệ. Cấm sụp đổ.\n\n"
        + (f"HỘI THOẠI TRƯỚC:\n{prior}\n" if prior else "")
        + f"PHIẾU CẢ PHIÊN:\n{_session_facts(recs, picked, scope, focus_image, inspect_id)}\n\n"
        f"CÂU HỎI: {q}\n"
        "Trả lời:"
    )
    try:
        raw = chat(prompt, think=False, num_predict=400, keep_alive="5m", extract=False)
        text = _keep_chat_vi(raw, gate_rec)
        names = [str(r.get("image_name") or "") for r in recs if r.get("image_name")]
        if (
            len(text) >= 24
            and not _is_echo(text, q)
            and (scope.get("topic") != "anhnao" or any(n and n in text for n in names))
        ):
            return text
    except Exception:
        pass
    return fallback

def summarize(ctx: dict) -> str:
    return summarize_fast(ctx)

def summarize_llm(ctx: dict) -> str:
    return chat(context_to_prompt(ctx), think=False)

def record_from_context(ctx: dict, summary: str) -> dict:
    return {
        "image_path": ctx["image_path"],
        "image_name": ctx["image_name"],
        "crack_ratio": ctx["crack_ratio"],
        "has_crack": ctx["has_crack"],
        "bbox": ctx.get("bbox"),
        "width": ctx.get("width"),
        "height": ctx.get("height"),
        "crack_pixels": ctx.get("crack_pixels"),
        "summary": summary,
        "vl_summary": ctx.get("vl_summary") or "",
        "detector": ctx.get("detector") or "conglomerate",
        "overlay_path": ctx.get("overlay_path") or "",
        "overlay_kind": ctx.get("overlay_kind") or "pred",
        "overlay_recall": ctx.get("overlay_recall"),
        "overlay_precision": ctx.get("overlay_precision"),
        "overlay_f1": ctx.get("overlay_f1"),
        "overlay_iou": ctx.get("overlay_iou"),
        "overlay_tp": ctx.get("overlay_tp"),
        "overlay_fp": ctx.get("overlay_fp"),
        "overlay_fn": ctx.get("overlay_fn"),
        "overlay_quality": ctx.get("overlay_quality") or "",
        "overlay_quality_vi": ctx.get("overlay_quality_vi") or "",
        "overlay_quality_en": ctx.get("overlay_quality_en") or "",
        "overlay_lang": ctx.get("overlay_lang") or "",
        "panel_path": ctx.get("panel_path") or "",
        "real_detection": is_real_detection(ctx),
        "source": Path(ctx["image_path"]).parts[-3] if len(Path(ctx["image_path"]).parts) >= 3 else "",
        "lat": ctx.get("lat"),
        "lon": ctx.get("lon"),
        "alt_m": ctx.get("alt_m"),
        "heading_deg": ctx.get("heading_deg"),
        "device": ctx.get("device"),
        "length_mm": ctx.get("length_mm"),
        "width_avg_mm": ctx.get("width_avg_mm"),
        "width_max_mm": ctx.get("width_max_mm"),
        "exif_source": ctx.get("exif_source"),
        "gsd_mm_per_px": ctx.get("gsd_mm_per_px"),
        "csv_dataset": ctx.get("csv_dataset"),
        "instances": ctx.get("instances") or [],
        "boxes_path": ctx.get("boxes_path") or "",
        "scene_kind": ctx.get("scene_kind") or "",
        "scene_reason": ctx.get("scene_reason") or "",
        "image_w": ctx.get("image_w") or ctx.get("width"),
        "image_h": ctx.get("image_h") or ctx.get("height"),
        "panel_layout": ctx.get("panel_layout") or {},
        "survey_object": ctx.get("survey_object") or "",
    }
