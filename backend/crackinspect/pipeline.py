from __future__ import annotations

import base64
import io
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image

from .agents import run_condition_pipeline
from .caption import describe_scene_caption, fallback_caption
from .config import (
    CAPTION_WORKERS,
    DESCRIBE_VL,
    MULTI_AGENT_MODE,
    OVERLAY_DIR,
    POST_WORKERS,
    SCENE_CAPTION,
    LAST_BATCH_PATH,
    SESSION_PATH,
    SHARPEN_DIR,
    SOURCE_KINDS,
    UPLOAD_DIR,
)
from .structure_inspect import extract_structure_report, prose_from_structure
from .crack_context import analyze_routed, set_overlay_lang
from .exif_meta import load_exif_for_image
from .gopro_deblur import release_gopro
from .instances import apply_scale, refine_instances_sift
from .realesrgan import release_realesrgan
from .report import format_problem, format_template_report
from .summarize import (
    describe_vl,
    format_detail_from_instances,
    is_real_detection,
    record_from_context,
    summarize_fast,
)

def _instance_crops(image_path: Path, instances: list[dict]) -> list[dict]:
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception:
        return list(instances)
    w, h = img.size
    out = []
    for inst in instances:
        row = dict(inst)
        box = inst.get("bbox") or {}
        x1 = max(0, int(box.get("x1", 0)))
        y1 = max(0, int(box.get("y1", 0)))
        x2 = min(w, int(box.get("x2", 0)) + 1)
        y2 = min(h, int(box.get("y2", 0)) + 1)
        if x2 > x1 and y2 > y1:
            crop = img.crop((x1, y1, x2, y2))
            crop.thumbnail((160, 160))
            buf = io.BytesIO()
            crop.save(buf, format="JPEG", quality=75)
            row["crop_data"] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        out.append(row)
    return out

def refine_record_sift(rec: dict) -> dict:
    if rec.get("sift_refined"):
        return rec
    raw = rec.get("image_path")
    path = Path(raw) if raw else UPLOAD_DIR / str(rec.get("image_name") or "")
    if not path.exists():
        alt = UPLOAD_DIR / str(rec.get("image_name") or "")
        if alt.exists():
            path = alt
        else:
            return rec
    try:
        rgb = np.array(Image.open(path).convert("RGB"))
    except Exception:
        return rec
    row = dict(rec)
    inst = refine_instances_sift(rgb, rec.get("instances") or [])
    row["instances"] = _instance_crops(path, inst)
    row["sift_refined"] = True
    row["image_w"] = int(rgb.shape[1])
    row["image_h"] = int(rgb.shape[0])
    return row

def refine_session_sift(records: list[dict]) -> list[dict]:
    out = [refine_record_sift(rec) if isinstance(rec, dict) else rec for rec in records]
    if out != records:
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        SESSION_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out

def _copy_upload(src: Path) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / src.name
    if Path(src).resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest

def purge_result_cache(image_names: list[str] | None = None) -> None:
    stems = {Path(name).stem for name in (image_names or []) if name}
    for folder in (SHARPEN_DIR, OVERLAY_DIR):
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file():
                continue
            if not stems or any(path.name.startswith(stem) for stem in stems):
                path.unlink(missing_ok=True)

def _heuristic_survey_object(ctx: dict) -> str:
    if ctx.get("scene_kind") == "hientruong":
        return "Cột / bệ bê tông (ảnh hiện trường)"
    if ctx.get("scene_kind") == "cancanh":
        return "Bề mặt bê tông (ảnh cận)"
    det = str(ctx.get("detector") or "").lower()
    if det.startswith("lcw"):
        return "Cột / bệ bê tông (ảnh hiện trường)"
    return "Bề mặt bê tông (ảnh cận)"

def _enrich_context(i: int, ctx: dict) -> dict:
    ctx = dict(ctx)
    ctx["upload_index"] = i
    ctx["real_detection"] = is_real_detection(ctx)
    path = Path(ctx["image_path"])
    ctx.update(load_exif_for_image(path))
    ctx["instances"] = _instance_crops(path, apply_scale(ctx.get("instances") or [], ctx))
    stats = summarize_fast(ctx)
    if DESCRIBE_VL:
        try:
            describe_vl(ctx, stats)
        except Exception:
            pass
    elif not ctx.get("survey_object"):
        ctx["survey_object"] = _heuristic_survey_object(ctx)

    condition = None
    if ctx["real_detection"] or MULTI_AGENT_MODE != "0":
        try:
            condition = run_condition_pipeline(path, ctx, stats=stats)
            ctx["condition"] = condition.to_dict()
        except Exception as exc:
            ctx["condition"] = None
            ctx["condition_error"] = str(exc)

    ctx["_stats"] = stats
    ctx["_condition_obj"] = condition
    return ctx

def _apply_caption(ctx: dict) -> dict:
    if not SCENE_CAPTION:
        ctx["structure_report"] = None
        ctx["description_vi"] = format_detail_from_instances(ctx)
        ctx["description_en"] = ""
        ctx["vl_summary"] = (ctx["description_vi"] or "").strip()
        return ctx

    try:
        report = extract_structure_report(ctx)
    except Exception as exc:
        report = None
        ctx["structure_error"] = str(exc)

    if isinstance(report, dict):
        ctx["structure_report"] = report
        ctx["description_vi"] = prose_from_structure(report, lang="vi")
        ctx["description_en"] = prose_from_structure(report, lang="en")
    else:
        ctx["structure_report"] = None
        try:
            vi, en = describe_scene_caption(ctx)
        except Exception as exc:
            vi, en = fallback_caption(ctx)
            vi = vi or format_detail_from_instances(ctx) or f"(VLM mô tả lỗi: {exc})"
        ctx["description_vi"] = vi
        ctx["description_en"] = en

    ctx["vl_summary"] = (ctx.get("description_vi") or "").strip()
    return ctx

def _to_record(i: int, ctx: dict) -> dict:
    stats = ctx.pop("_stats", summarize_fast(ctx))
    condition = ctx.pop("_condition_obj", None)
    vl = (ctx.get("vl_summary") or "").strip()
    rec = record_from_context(ctx, stats if not vl else f"{stats} {vl}")
    rec["upload_index"] = i
    rec["stats"] = stats
    rec["vl_summary"] = vl
    rec["description_vi"] = ctx.get("description_vi") or ""
    rec["description_en"] = ctx.get("description_en") or ""
    rec["real_detection"] = ctx["real_detection"]
    rec["overlay_path"] = ctx.get("overlay_path") or rec.get("overlay_path") or ""
    rec["overlay_kind"] = ctx.get("overlay_kind") or rec.get("overlay_kind") or "pred"
    rec["overlay_recall"] = ctx.get("overlay_recall")
    rec["overlay_precision"] = ctx.get("overlay_precision")
    rec["overlay_f1"] = ctx.get("overlay_f1")
    rec["overlay_iou"] = ctx.get("overlay_iou")
    rec["overlay_tp"] = ctx.get("overlay_tp")
    rec["overlay_fp"] = ctx.get("overlay_fp")
    rec["overlay_fn"] = ctx.get("overlay_fn")
    rec["overlay_quality"] = ctx.get("overlay_quality") or ""
    rec["overlay_quality_vi"] = ctx.get("overlay_quality_vi") or ""
    rec["overlay_quality_en"] = ctx.get("overlay_quality_en") or ""
    rec["overlay_lang"] = ctx.get("overlay_lang") or ""
    rec["panel_path"] = ctx.get("panel_path") or ""
    rec["instances"] = ctx.get("instances") or []
    rec["boxes_path"] = ctx.get("boxes_path") or ""
    rec["scene_kind"] = ctx.get("scene_kind") or ""
    rec["scene_reason"] = ctx.get("scene_reason") or ""
    rec["source_kind"] = ctx.get("source_kind") or "unknown"
    rec["structure_report"] = ctx.get("structure_report")
    rec["image_w"] = ctx.get("image_w") or rec.get("image_w") or rec.get("width")
    rec["image_h"] = ctx.get("image_h") or rec.get("image_h") or rec.get("height")
    rec["panel_layout"] = ctx.get("panel_layout") or rec.get("panel_layout") or {}
    if condition is not None:
        cond = condition.to_dict()
        rec["condition"] = cond
        rec["grade"] = cond.get("final", {}).get("grade")
    else:
        rec["condition"] = ctx.get("condition")
        rec["grade"] = None
    return rec

def analyze_images(
    image_paths: list[str | Path],
    source_kind: str = "unknown",
    lang: str = "vi",
) -> list[dict]:
    release_gopro()
    release_realesrgan()
    kind = (source_kind or "unknown").strip().lower()
    if kind not in SOURCE_KINDS:
        kind = "unknown"
    set_overlay_lang(lang)
    paths = [_copy_upload(Path(p)) for p in image_paths]
    purge_result_cache([path.name for path in paths])
    contexts = analyze_routed(paths)
    for ctx in contexts:
        ctx["source_kind"] = kind

    n = len(contexts)
    enriched: list[dict] = [None] * n  # type: ignore[list-item]
    workers = min(POST_WORKERS, max(1, n))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_enrich_context, i, ctx): i for i, ctx in enumerate(contexts, 1)}
        for fut in as_completed(futs):
            i = futs[fut]
            enriched[i - 1] = fut.result()

    if SCENE_CAPTION and n:
        cap_workers = min(CAPTION_WORKERS, n)
        with ThreadPoolExecutor(max_workers=cap_workers) as pool:
            list(pool.map(_apply_caption, enriched))
    else:
        for ctx in enriched:
            _apply_caption(ctx)

    records = [_to_record(i, ctx) for i, ctx in enumerate(enriched, 1)]
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_BATCH_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    merged = _merge_session(records)
    SESSION_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged

def _merge_session(new_records: list[dict]) -> list[dict]:
    old: list[dict] = []
    if SESSION_PATH.exists():
        try:
            raw = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
            old = [r for r in raw if isinstance(r, dict)]
        except Exception:
            old = []
    by_name: dict[str, dict] = {}
    for rec in old + new_records:
        name = str(rec.get("image_name") or "")
        if name:
            by_name[name] = rec
    return list(by_name.values())

def analyze_bundle(
    image_paths: list[str | Path],
    source_kind: str = "unknown",
    lang: str = "vi",
) -> dict:
    records = analyze_images(image_paths, source_kind=source_kind, lang=lang)
    return {
        "records": records,
        "problem": format_problem(records),
        "report": format_template_report(records),
    }
