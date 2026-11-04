from __future__ import annotations

import csv
import re
from pathlib import Path

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS

from .config import ANNOTATED_ROOT

_CSV_INDEX: dict[str, dict] | None = None
_CSV_FLOATS = (
    "gsd_mm_per_px",
    "crack_pixels",
    "length_px",
    "length_mm",
    "width_avg_px",
    "width_avg_mm",
    "width_max_px",
    "width_max_mm",
    "lat",
    "lon",
    "alt_m",
    "heading_deg",
)

_LEN_RE = re.compile(r"length[^\d]*([\d.]+)\s*px(?:\s*\(([\d.]+)\s*mm\))?", re.I)
_WAVG_RE = re.compile(r"width avg[^\d]*([\d.]+)\s*px(?:\s*\(([\d.]+)\s*mm\))?", re.I)
_WMAX_RE = re.compile(r"width max[^\d]*([\d.]+)\s*px(?:\s*\(([\d.]+)\s*mm\))?", re.I)

def _ratio(values) -> float:
    if isinstance(values, tuple) and len(values) == 2 and values[1]:
        return float(values[0]) / float(values[1])
    return float(values)

def _dms(values, ref: str) -> float:
    parts = list(values)
    while len(parts) < 3:
        parts.append(0)
    dec = _ratio(parts[0]) + _ratio(parts[1]) / 60 + _ratio(parts[2]) / 3600
    if str(ref).upper() in {"S", "W"}:
        dec = -dec
    return round(dec, 7)

def _user_comment(val) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        if val.startswith(b"UNICODE"):
            return val[8:].decode("utf-16-le", errors="ignore")
        if val.startswith(b"ASCII"):
            return val[8:].decode("ascii", errors="ignore")
        return val.decode("utf-8", errors="ignore")
    return str(val)

def _parse_measures(text: str) -> dict:
    out: dict = {}
    if not text:
        return out
    m = _LEN_RE.search(text)
    if m:
        out["length_px"] = float(m.group(1))
        if m.group(2):
            out["length_mm"] = float(m.group(2))
    m = _WAVG_RE.search(text)
    if m:
        out["width_avg_px"] = float(m.group(1))
        if m.group(2):
            out["width_avg_mm"] = float(m.group(2))
    m = _WMAX_RE.search(text)
    if m:
        out["width_max_px"] = float(m.group(1))
        if m.group(2):
            out["width_max_mm"] = float(m.group(2))
    lp, lm = out.get("length_px"), out.get("length_mm")
    if lp and lm and out.get("width_max_px") is not None and out.get("width_max_mm") is None:
        out["width_max_mm"] = round(out["width_max_px"] * lm / lp, 2)
    return out

def read_exif(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        im = Image.open(path)
        ex = im.getexif()
    except Exception:
        return {}
    if not ex:
        return {}

    tags = {TAGS.get(k, k): v for k, v in ex.items()}
    gps_raw = {}
    try:
        raw = ex.get_ifd(0x8825)
        gps_raw = {GPSTAGS.get(k, k): raw[k] for k in raw}
    except Exception:
        pass
    exif_ifd = {}
    try:
        raw = ex.get_ifd(0x8769)
        exif_ifd = {TAGS.get(k, k): v for k, v in raw.items()}
    except Exception:
        pass

    desc = str(tags.get("ImageDescription") or "")
    comment = _user_comment(exif_ifd.get("UserComment"))
    measures = _parse_measures(desc) or _parse_measures(comment)

    lat = lon = None
    if gps_raw.get("GPSLatitude") is not None:
        lat = _dms(gps_raw["GPSLatitude"], gps_raw.get("GPSLatitudeRef") or "N")
    if gps_raw.get("GPSLongitude") is not None:
        lon = _dms(gps_raw["GPSLongitude"], gps_raw.get("GPSLongitudeRef") or "E")
    alt = gps_raw.get("GPSAltitude")
    heading = gps_raw.get("GPSImgDirection")
    make = tags.get("Make")
    model = tags.get("Model")
    device = " ".join(p for p in (str(make).strip() if make else "", str(model).strip() if model else "") if p)
    if make and model and str(model).startswith(str(make)):
        device = str(model).strip()

    out = {
        "exif_file": str(path),
        "exif_make": str(make).strip() if make else None,
        "exif_model": str(model).strip() if model else None,
        "device": device or None,
        "lat": lat,
        "lon": lon,
        "alt_m": float(alt) if alt is not None else None,
        "heading_deg": float(heading) if heading is not None else None,
        "datetime": tags.get("DateTime") or exif_ifd.get("DateTimeOriginal"),
    }
    out.update(measures)
    if lat is None and lon is None and not device and not measures:
        return {}
    return out

def annotated_meta_path(image_path: Path) -> Path | None:
    stem = Path(image_path).stem
    if stem.endswith("_meta"):
        stem = stem[:-5]
    for split in ("Test", "Train"):
        cand = ANNOTATED_ROOT / split / f"{stem}_meta.jpg"
        if cand.exists():
            return cand
    return None

def annotated_gt_path(image_path: Path) -> Path | None:
    stem = Path(image_path).stem
    if stem.endswith("_meta"):
        stem = stem[:-5]
    for split in ("Test", "Train"):
        cand = ANNOTATED_ROOT / split / f"{stem}_gt.png"
        if cand.exists():
            return cand
    return None

def _norm_stem(name: str) -> str:
    stem = Path(name).stem
    if stem.endswith("_meta"):
        stem = stem[:-5]
    if stem.endswith("_gt"):
        stem = stem[:-3]
    return stem.lower()

def _float_or_none(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def csv_index() -> dict[str, dict]:
    global _CSV_INDEX
    if _CSV_INDEX is not None:
        return _CSV_INDEX
    path = ANNOTATED_ROOT / "metadata.csv"
    index: dict[str, dict] = {}
    if not path.exists():
        _CSV_INDEX = index
        return index
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rec = {
                "csv_split": row.get("split"),
                "csv_dataset": row.get("dataset"),
                "device": (row.get("device") or "").strip() or None,
                "mask_source": row.get("mask_source"),
            }
            for key in _CSV_FLOATS:
                rec[key] = _float_or_none(row.get(key))
            for raw in (row.get("output"), row.get("input"), row.get("file")):
                if raw:
                    index.setdefault(_norm_stem(raw), rec)
    _CSV_INDEX = index
    return index

def lookup_csv(image_path: Path) -> dict:
    rec = csv_index().get(_norm_stem(Path(image_path).name))
    return dict(rec) if rec else {}

def _merge_meta(csv_row: dict, exif: dict) -> dict:
    out = dict(csv_row)
    for key, val in exif.items():
        if val is None or val == "":
            continue
        if out.get(key) in (None, ""):
            out[key] = val
        elif key in {"lat", "lon", "alt_m", "heading_deg", "device"} and exif.get("lat") is not None:
            out[key] = val
        elif key.startswith("exif_") or key in {"datetime", "exif_file"}:
            out[key] = val
    sources = []
    if csv_row:
        sources.append("csv")
    if exif:
        sources.append("exif")
    out["exif_source"] = "+".join(sources) if sources else None
    return out

def load_exif_for_image(image_path: Path) -> dict:
    image_path = Path(image_path)
    csv_row = lookup_csv(image_path)
    direct = read_exif(image_path)
    twin = annotated_meta_path(image_path)
    twin_exif = {}
    if twin and twin.resolve() != image_path.resolve():
        twin_exif = read_exif(twin)
    exif = direct if direct.get("lat") is not None else (twin_exif or direct)
    if not csv_row and not exif:
        return {}
    return _merge_meta(csv_row, exif)
