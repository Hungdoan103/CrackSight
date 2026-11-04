from __future__ import annotations

import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_CLOSE_NAME = re.compile(
    r"(cfd|crack500|conglomerate|close[\s_-]?up|cancanh|macro|zoom)",
    re.I,
)
_FIELD_NAME = re.compile(
    r"(lcw|hientruong|field|scene|bridge|pier|column|abutment|unknown_field)",
    re.I,
)

def _load_rgb(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB"))

def _features(rgb: np.ndarray) -> dict[str, float]:
    small = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    coarse = cv2.GaussianBlur(cv2.resize(gray, (48, 48), interpolation=cv2.INTER_AREA), (3, 3), 0)
    gx = cv2.Sobel(coarse, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(coarse, cv2.CV_32F, 0, 1, ksize=3)
    coarse_mag = float(np.mean(np.sqrt(gx * gx + gy * gy)))
    edges = cv2.Canny(gray, 50, 140)
    edge_density = float(edges.mean())
    lap = cv2.Laplacian(gray, cv2.CV_32F)
    tiles = [
        float(lap[i * 64 : (i + 1) * 64, j * 64 : (j + 1) * 64].std())
        for i in range(4)
        for j in range(4)
    ]
    tile_cv = float(np.std(tiles) / (np.mean(tiles) + 1e-6))
    top = float(gray[:64].mean())
    bot = float(gray[192:].mean())
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=60, minLineLength=90, maxLineGap=8
    )
    long_n = 0 if lines is None else float(len(lines))
    return {
        "coarse": coarse_mag,
        "edge": edge_density,
        "tile_cv": tile_cv,
        "sat": float(hsv[:, :, 1].mean()),
        "dTB": top - bot,
        "long": long_n,
        "hue_std": float(hsv[:, :, 0].std()),
        "w": float(rgb.shape[1]),
        "h": float(rgb.shape[0]),
    }

def _score(f: dict[str, float]) -> tuple[float, list[str]]:
    s = 0.0
    reasons: list[str] = []
    if f["tile_cv"] >= 0.18:
        s += 2.0
        reasons.append("skew_field")
    elif f["tile_cv"] <= 0.14:
        s -= 2.0
        reasons.append("uniform_close")
    if abs(f["dTB"]) >= 25:
        s += 1.2
        reasons.append("light_split")
    if f["long"] >= 8 and f["tile_cv"] >= 0.16:
        s += 1.0
        reasons.append("long_structure")
    if f["edge"] >= 70 and f["tile_cv"] <= 0.15:
        s -= 1.5
        reasons.append("smooth_edges")
    if f["sat"] < 28 and f["hue_std"] < 35 and f["tile_cv"] < 0.16:
        s -= 1.0
        reasons.append("gray_surface")
    if f["coarse"] < 50:
        s -= 1.2
        reasons.append("low_coarse")
    if f["coarse"] > 120 and f["tile_cv"] > 0.18:
        s += 1.0
        reasons.append("high_coarse")
    if max(f["w"], f["h"]) <= 480 and f["tile_cv"] < 0.20:
        s -= 0.8
        reasons.append("small_crop")
    return s, reasons

def classify_scene_cv(path: Path) -> tuple[str, str]:
    path = Path(path)
    name = path.name
    if _CLOSE_NAME.search(name):
        return "conglomerate", f"name_close:{name}"
    if _FIELD_NAME.search(name):
        return "lcw", f"name_field:{name}"

    try:
        rgb = _load_rgb(path)
        f = _features(rgb)
        score, bits = _score(f)
    except Exception:
        w, h = Image.open(path).size
        if max(w, h) < 480:
            return "conglomerate", f"fallback_size:{w}x{h}"
        return "lcw", f"fallback_size:{w}x{h}"

    codes = ",".join(bits) if bits else "default"
    if score >= 0:
        return "lcw", f"cv_field:{score:+.1f}:{codes}"
    return "conglomerate", f"cv_close:{score:+.1f}:{codes}"
