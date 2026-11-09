from __future__ import annotations

import base64
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from io import BytesIO

import numpy as np
from PIL import Image

from crackinspect.config import (
    ANNOTATED_ROOT,
    CAPTION_WORKERS,
    CONGLOMERATE_WEIGHTS,
    DESCRIBE_VL,
    DETECT_BATCH,
    DETECT_SIFT,
    KEEP_MODELS,
    LCW_RETRY,
    LCW_WEIGHTS,
    LIDAR_DATA_ROOT,
    LIDAR_MAP_ROOT,
    LIDAR_SCENE_DIR,
    MULTI_AGENT_MODE,
    OVERLAY_DIR,
    POST_WORKERS,
    SAMPLE_ANNOTATED,
    SAMPLE_LCW,
    SAMPLE_UNKNOWN,
    SCENE_CAPTION,
    LAST_BATCH_PATH,
    SESSION_PATH,
    SHARPEN_DIR,
    SOURCE_KINDS,
    STORE_DIR,
    UPLOAD_DIR,
    VLM_ROUTE,
)
from crackinspect.agents.orchestrate import load_condition_rules, load_last_condition
from crackinspect.lasViewer import build_las_viewer, build_voxel_viewer, list_las_files
from crackinspect.lidarMap import build_overlay, list_map_las
from crackinspect.lidar3d import (
    generate_from_las,
    generate_scene_via_llama_server,
    model_status as lidar_3d_status,
    render_birdeye_preview,
)
from crackinspect.realesrgan import cache_path, enhance_inspect_jpeg, release_realesrgan
from crackinspect.geocode import reverse_geocode
from crackinspect.pipeline import analyze_bundle, refine_session_sift
from crackinspect.report import preview_path, scene_text
from crackinspect.summarize import answer_chat, build_review, describe_closeup, format_closeup

app = FastAPI(title="CrackInspect", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media/overlays", StaticFiles(directory=str(OVERLAY_DIR)), name="overlays")

def _b64_thumb(path: str | Path | None, max_side: int = 180) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    img = Image.open(p).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img.thumbnail((max_side, max_side))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=78)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def _b64_jpeg(path: str | Path | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    suffix = p.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    img = Image.open(p).convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, float):
        return float(value)
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    try:
        return json.loads(json.dumps(value, default=str))
    except TypeError:
        return str(value)

def _original_path(rec: dict) -> Path | None:
    raw = rec.get("image_path")
    if raw:
        p = Path(raw)
        if p.exists():
            return p
    name = rec.get("image_name")
    if name:
        cand = UPLOAD_DIR / str(name)
        if cand.exists():
            return cand
    return None

def _public_record(rec: dict) -> dict:
    preview = preview_path(rec)
    out = _json_safe(rec)
    narrative = scene_text(rec) or rec.get("description_vi") or rec.get("vl_summary") or ""
    out["description_vi"] = rec.get("description_vi") or narrative
    out["description_en"] = rec.get("description_en") or ""
    out["vl_summary"] = narrative
    out["review"] = build_review(rec)
    out["preview_url"] = f"/media/overlays/{Path(preview).name}" if preview else ""
    out["preview_data"] = _b64_jpeg(preview)
    out["original_data"] = _b64_jpeg(_original_path(rec))
    panel = rec.get("panel_path")
    out["panel_data"] = _b64_jpeg(panel) if panel else ""
    out.pop("image_path", None)
    return out

def _public_bundle(bundle: dict) -> dict:
    rows = bundle["records"]
    if len(rows) <= 1:
        records = [_public_record(r) for r in rows]
    else:
        workers = min(POST_WORKERS, len(rows))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            records = list(pool.map(_public_record, rows))
    return {
        "records": records,
        "problem": bundle["problem"],
        "report": bundle["report"],
    }

@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "weights": {
            "conglomerate": CONGLOMERATE_WEIGHTS.exists(),
            "lcw": LCW_WEIGHTS.exists(),
        },
        "speed": {
            "vlm_route": VLM_ROUTE,
            "multi_agent": MULTI_AGENT_MODE,
            "scene_caption": SCENE_CAPTION,
            "describe_vl": DESCRIBE_VL,
            "detect_sift": DETECT_SIFT,
            "lcw_retry": LCW_RETRY,
            "keep_models": KEEP_MODELS,
            "detect_batch": DETECT_BATCH,
            "post_workers": POST_WORKERS,
            "caption_workers": CAPTION_WORKERS,
        },
        "annotated_csv": (ANNOTATED_ROOT / "metadata.csv").exists(),
        "sample_annotated": SAMPLE_ANNOTATED.exists(),
        "lidar_3d": lidar_3d_status(),
        "lidar_data": {
            "root": str(LIDAR_DATA_ROOT),
            "exists": LIDAR_DATA_ROOT.is_dir(),
            "las_count": len(list(LIDAR_DATA_ROOT.glob("*.las"))) if LIDAR_DATA_ROOT.is_dir() else 0,
        },
    }

@app.get("/lidar-3d/status")
def lidar_3d_status_route() -> dict:
    status = lidar_3d_status()
    las = sorted(LIDAR_DATA_ROOT.glob("*.las")) if LIDAR_DATA_ROOT.is_dir() else []
    status["lidar_data"] = {
        "root": str(LIDAR_DATA_ROOT),
        "files": [{"name": p.name, "bytes": p.stat().st_size} for p in las],
    }
    return status

@app.get("/lidar/files")
def lidar_files() -> dict:
    return {"root": str(LIDAR_DATA_ROOT), "files": list_las_files()}

@app.get("/lidar/map-files")
def lidar_map_files() -> dict:
    return {"root": str(LIDAR_MAP_ROOT), "files": list_map_las()}

@app.get("/lidar/map-overlay")
def lidar_map_overlay(max_points: int = 2000000, force: int = 0) -> dict:
    try:
        return build_overlay(max_points=max_points, force=bool(force))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

@app.post("/lidar/build")
def lidar_build(names: str = "", max_points: int = 200000) -> dict:
    selected = [part.strip() for part in names.split(",") if part.strip()] or None
    try:
        return build_las_viewer(selected, max_points=max(1000, min(int(max_points), 500_000)))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

@app.post("/lidar/build-voxel")
def lidar_build_voxel(names: str = "", max_points: int = 60000) -> dict:
    selected = [part.strip() for part in names.split(",") if part.strip()] or None
    try:
        return build_voxel_viewer(
            selected,
            max_points=max(1000, min(int(max_points), 200_000)),
            out_name="qwen3d_223582_voxel",
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

@app.get("/lidar/view/{name}")
def lidar_view(name: str) -> FileResponse:
    target = (LIDAR_SCENE_DIR / Path(name).name).resolve()
    if not str(target).startswith(str(LIDAR_SCENE_DIR.resolve())):
        raise HTTPException(403, "Invalid path")
    if not target.is_file():
        raise HTTPException(404, f"Viewer not found: {name}. Call POST /lidar/build first.")
    return FileResponse(target, media_type="text/html")

@app.post("/lidar-3d/preview")
def lidar_3d_preview(names: str = "", max_points: int = 80000) -> dict:
    selected = [part.strip() for part in names.split(",") if part.strip()] or None
    try:
        return render_birdeye_preview(selected, max_points=max(1000, min(int(max_points), 200_000)))
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

@app.post("/lidar-3d/from-las")
def lidar_3d_from_las(names: str = "", prompt: str = "", max_points: int = 80000) -> dict:
    selected = [part.strip() for part in names.split(",") if part.strip()] or None
    try:
        return generate_from_las(
            selected,
            prompt=prompt.strip() or None,
            max_points=max(1000, min(int(max_points), 200_000)),
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

@app.post("/lidar-3d/scene")
async def lidar_3d_scene(
    prompt: str = (
        "Create one self-contained HTML Three.js scene that visualizes a road "
        "LiDAR inspection corridor with readable depth and solid spatial relationships."
    ),
    file: UploadFile = File(None),
) -> dict:
    image_path: Path | None = None
    if file is not None and file.filename:
        LIDAR_SCENE_DIR.mkdir(parents=True, exist_ok=True)
        image_path = LIDAR_SCENE_DIR / Path(file.filename).name
        image_path.write_bytes(await file.read())
    try:
        return generate_scene_via_llama_server(prompt, image_path, out_stem="qwen3d_manual")
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc

@app.get("/condition/rules")
def condition_rules() -> dict:
    try:
        return load_condition_rules()
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc

@app.get("/condition/last")
def condition_last() -> dict:
    data = load_last_condition()
    if not data:
        return {"condition": None}
    return {"condition": data}

@app.get("/last")
def last_session() -> dict:
    """Return the latest Detect batch only (not accumulated history)."""
    src = LAST_BATCH_PATH if LAST_BATCH_PATH.exists() else SESSION_PATH
    if not src.exists():
        return {"records": [], "problem": "", "report": ""}
    try:
        records = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return {"records": [], "problem": "", "report": ""}
    if not isinstance(records, list):
        return {"records": [], "problem": "", "report": ""}
    records = refine_session_sift([r for r in records if isinstance(r, dict)])
    return {
        "records": [_public_record(r) for r in records],
        "problem": "",
        "report": "",
    }

@app.get("/session/gps")
def session_gps(lang: str = "en", include_all: int = 0) -> dict:
    src = SESSION_PATH if int(include_all or 0) else LAST_BATCH_PATH
    if not src.exists():
        return {"points": [], "count": 0}
    try:
        records = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        return {"points": [], "count": 0}
    if not isinstance(records, list):
        return {"points": [], "count": 0}

    lang_norm = "vi" if str(lang).lower().startswith("vi") else "en"
    points: list[dict] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        lat, lon = rec.get("lat"), rec.get("lon")
        try:
            lat_f = float(lat) if lat is not None else None
            lon_f = float(lon) if lon is not None else None
        except (TypeError, ValueError):
            continue
        if lat_f is None or lon_f is None:
            continue
        if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
            continue
        thumb = _b64_thumb(_original_path(rec)) or _b64_thumb(preview_path(rec))
        alt = rec.get("alt_m")
        try:
            alt_f = float(alt) if alt is not None else None
        except (TypeError, ValueError):
            alt_f = None
        instances = rec.get("instances") if isinstance(rec.get("instances"), list) else []
        n_cracks = len(instances)
        address = reverse_geocode(lat_f, lon_f, lang=lang_norm)
        points.append(
            {
                "image_name": str(rec.get("image_name") or ""),
                "lat": lat_f,
                "lon": lon_f,
                "alt_m": alt_f,
                "heading_deg": rec.get("heading_deg"),
                "detector": rec.get("detector") or "",
                "scene_kind": rec.get("scene_kind") or "",
                "has_crack": bool(rec.get("has_crack") or n_cracks),
                "n_cracks": n_cracks,
                "exif_source": rec.get("exif_source") or "",
                "address": address,
                "thumb": thumb,
            }
        )
    return {"points": points, "count": len(points)}

def _is_small_box(bw: int, bh: int) -> bool:
    return max(bw, bh) < 48

def _shift_fit(x1: float, y1: float, x2: float, y2: float, src_w: int, src_h: int) -> tuple[int, int, int, int]:
    if x1 < 0:
        x2 -= x1
        x1 = 0
    if y1 < 0:
        y2 -= y1
        y1 = 0
    if x2 > src_w:
        x1 = max(0, x1 - (x2 - src_w))
        x2 = src_w
    if y2 > src_h:
        y1 = max(0, y1 - (y2 - src_h))
        y2 = src_h
    return max(0, int(x1)), max(0, int(y1)), min(src_w, int(x2)), min(src_h, int(y2))

def _inspect_box(box: dict, src_w: int, src_h: int) -> tuple[int, int, int, int]:
    bw = max(1, int(box.get("x2", 0)) - int(box.get("x1", 0)) + 1)
    bh = max(1, int(box.get("y2", 0)) - int(box.get("y1", 0)) + 1)
    if _is_small_box(bw, bh):
        pad = max(8, int(max(bw, bh) * 0.55))
        min_side = max(36, max(bw, bh) + 16)
    else:
        pad = max(14, int(max(bw, bh) * 0.7))
        min_side = 72
    x1 = int(box.get("x1", 0)) - pad
    y1 = int(box.get("y1", 0)) - pad
    x2 = int(box.get("x2", 0)) + 1 + pad
    y2 = int(box.get("y2", 0)) + 1 + pad
    if x2 - x1 < min_side:
        extra = (min_side - (x2 - x1)) / 2
        x1 -= extra
        x2 += extra
    if y2 - y1 < min_side:
        extra = (min_side - (y2 - y1)) / 2
        y1 -= extra
        y2 += extra
    return _shift_fit(x1, y1, x2, y2, src_w, src_h)

@app.get("/sharpen")
def sharpen(image_name: str, id: int) -> dict:
    if not SESSION_PATH.exists():
        raise HTTPException(404, "Chưa có phiên phân tích.")
    records = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    rec = next((r for r in records if isinstance(r, dict) and r.get("image_name") == image_name), None)
    if rec is None:
        raise HTTPException(404, f"Không thấy ảnh {image_name}.")
    inst = next((i for i in rec.get("instances") or [] if int(i.get("id", -1)) == id), None)
    if inst is None or not inst.get("bbox"):
        raise HTTPException(404, f"Không thấy vết #{id}.")
    cached = cache_path(image_name, id)
    box = inst["bbox"]
    src = _original_path(rec)
    if src is None or not src.exists():
        raise HTTPException(404, "Không thấy ảnh gốc.")
    img = Image.open(src).convert("RGB")
    sw, sh = img.size
    x1, y1, x2, y2 = _inspect_box(box, sw, sh)
    try:
        data = enhance_inspect_jpeg(np.array(img), (x1, y1, x2, y2))
        cached.write_bytes(base64.b64decode(data.split(",", 1)[1]))
        return {"data": data, "source": "realesrgan", "mode": "sr_then_nearest"}
    except Exception as exc:
        crop = np.array(img.crop((x1, y1, max(x2, x1 + 1), max(y2, y1 + 1))))
        buf = BytesIO()
        Image.fromarray(crop).save(buf, format="JPEG", quality=90)
        fallback = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        return {"data": fallback, "source": "fallback", "error": str(exc)}

def _closeup_json_path(image_name: str, inst_id: int) -> Path:
    SHARPEN_DIR.mkdir(parents=True, exist_ok=True)
    return SHARPEN_DIR / f"{Path(image_name).stem}_{inst_id}_closeup.json"

def _closeup_crop_path(image_name: str, inst_id: int) -> Path:
    SHARPEN_DIR.mkdir(parents=True, exist_ok=True)
    return SHARPEN_DIR / f"{Path(image_name).stem}_{inst_id}_closeup.jpg"

def _as_closeup_fields(raw) -> dict | None:
    if not (isinstance(raw, dict) and raw.get("length") and raw.get("detail")):
        return None
    detail = str(raw.get("detail") or "")
    if re.search(
        r"(?i)vị\s*trí\s*:|\blike\b|trên bề mặt vật thể|cấm cụm|crop vết nứt|"
        r"không số đo|thẳng,\s*cong,\s*mạng|\(\s*thẳng|đang thấy trên ảnh|"
        r"có cong không|hay phân nhánh|có mạng lưới không|mô tả đúng hình dạng",
        detail,
    ):
        return None
    fields = dict(raw)
    fields["text"] = format_closeup(fields)
    return fields

def _save_instance_closeup(records: list, image_name: str, inst_id: int, fields: dict) -> None:
    rec = next((r for r in records if isinstance(r, dict) and r.get("image_name") == image_name), None)
    if rec is None:
        return
    inst = next((i for i in rec.get("instances") or [] if int(i.get("id", -1)) == inst_id), None)
    if inst is None:
        return
    inst["closeup"] = fields
    SESSION_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

@app.get("/closeup")
def closeup(image_name: str, id: int) -> dict:
    if not SESSION_PATH.exists():
        raise HTTPException(404, "Chưa có phiên phân tích.")
    records = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    rec = next((r for r in records if isinstance(r, dict) and r.get("image_name") == image_name), None)
    if rec is None:
        raise HTTPException(404, f"Không thấy ảnh {image_name}.")
    inst = next((i for i in rec.get("instances") or [] if int(i.get("id", -1)) == id), None)
    if inst is None or not inst.get("bbox"):
        raise HTTPException(404, f"Không thấy vết #{id}.")
    cached = _closeup_json_path(image_name, id)
    release_realesrgan()
    sharp = cache_path(image_name, id)
    crop_file = _closeup_crop_path(image_name, id)
    if sharp.exists():
        vision_path = sharp
    else:
        src = _original_path(rec)
        if src is None or not src.exists():
            raise HTTPException(404, "Không thấy ảnh gốc.")
        img = Image.open(src).convert("RGB")
        sw, sh = img.size
        x1, y1, x2, y2 = _inspect_box(inst["bbox"], sw, sh)
        img.crop((x1, y1, max(x2, x1 + 1), max(y2, y1 + 1))).save(crop_file, format="JPEG", quality=90)
        vision_path = crop_file
    fields = describe_closeup(vision_path, id, rec)
    cached.write_text(json.dumps(fields, ensure_ascii=False), encoding="utf-8")
    try:
        _save_instance_closeup(records, image_name, id, fields)
    except Exception:
        pass
    return {"source": "qwen", **fields}

@app.get("/samples")
def samples() -> dict:
    items = []
    for key, path, label in (
        ("cfd001", SAMPLE_ANNOTATED, "CFD_001"),
        ("cfd005", ANNOTATED_ROOT / "Test" / "CFD_005_meta.jpg", "CFD_005"),
        ("lcw30", SAMPLE_LCW, "LCW-30 ô 4"),
        ("unknown", SAMPLE_UNKNOWN, "Ảnh lạ"),
    ):
        if path.exists():
            items.append({"name": key, "label": label, "thumb": _b64_thumb(path)})
    return {"samples": items}

@app.post("/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    source_kind: str = Form("unknown"),
    lang: str = Form("vi"),
) -> dict:
    if not files:
        raise HTTPException(400, "Cần ít nhất một ảnh.")
    kind = (source_kind or "unknown").strip().lower()
    if kind not in SOURCE_KINDS:
        kind = "unknown"
    ui_lang = "en" if str(lang or "").lower().startswith("en") else "vi"
    saved: list[Path] = []
    for item in files:
        name = Path(item.filename or "upload.jpg").name
        dest = UPLOAD_DIR / name
        if dest.exists():
            stem, suf = dest.stem, dest.suffix
            n = 2
            while True:
                cand = UPLOAD_DIR / f"{stem}_{n}{suf}"
                if not cand.exists():
                    dest = cand
                    break
                n += 1
        dest.write_bytes(await item.read())
        saved.append(dest)
    return _public_bundle(analyze_bundle(saved, source_kind=kind, lang=ui_lang))

@app.post("/chat")
def chat_qa(payload: dict) -> dict:
    image_name = str(payload.get("image_name") or "").strip()
    question = str(payload.get("question") or "").strip()
    inspect_id = payload.get("inspect_id")
    try:
        inspect_id = int(inspect_id) if inspect_id is not None else None
    except (TypeError, ValueError):
        inspect_id = None
    if not question:
        raise HTTPException(400, "Cần câu hỏi.")
    if not SESSION_PATH.exists():
        raise HTTPException(404, "Chưa có phiên phân tích.")
    records = [r for r in json.loads(SESSION_PATH.read_text(encoding="utf-8")) if isinstance(r, dict)]
    if not records:
        raise HTTPException(404, "Chưa có ảnh trong phiên.")
    focus = image_name if any(r.get("image_name") == image_name for r in records) else None
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    history = [
        {"role": str(m.get("role") or ""), "text": str(m.get("text") or "")}
        for m in history
        if isinstance(m, dict)
    ][-8:]
    release_realesrgan()
    names = [str(r.get("image_name") or "") for r in records if r.get("image_name")]
    return {
        "answer": answer_chat(records, question, inspect_id, focus, history),
        "images": names,
        "image_name": focus,
    }

@app.post("/analyze-sample")
def analyze_sample(name: str = "cfd001") -> dict:
    samples = {
        "cfd001": SAMPLE_ANNOTATED,
        "cfd005": ANNOTATED_ROOT / "Test" / "CFD_005_meta.jpg",
        "lcw30": SAMPLE_LCW,
        "unknown": SAMPLE_UNKNOWN,
    }
    path = samples.get(name)
    if path is None or not path.exists():
        raise HTTPException(404, f"Không có ảnh mẫu {name}.")
    return _public_bundle(analyze_bundle([path]))

@app.get("/media/file")
def media_file(path: str) -> FileResponse:
    target = Path(path).resolve()
    allowed = (STORE_DIR.resolve(), OVERLAY_DIR.resolve(), UPLOAD_DIR.resolve())
    if not any(str(target).startswith(str(root)) for root in allowed):
        raise HTTPException(403, "Đường dẫn không hợp lệ.")
    if not target.exists():
        raise HTTPException(404, "Không thấy file.")
    return FileResponse(target)
