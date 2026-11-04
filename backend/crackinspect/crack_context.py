from __future__ import annotations

import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .config import (
    CONGLOMERATE_WEIGHTS,
    DETECT_BATCH,
    INPUT_SIZE,
    KEEP_MODELS,
    LCW_RETRY,
    LCW_WEIGHTS,
    POST_WORKERS,
    TRAINING_DIR,
    VLM_ROUTE,
)
from .overlay import save_overlay
from .scene_classify import classify_scene_cv

WEIGHTS = {
    "conglomerate": CONGLOMERATE_WEIGHTS,
    "lcw": LCW_WEIGHTS,
}

try:
    from torchvision.models.utils import load_state_dict_from_url  # noqa: F401
except Exception:
    import torch.hub

    _utils = types.ModuleType("torchvision.models.utils")
    _utils.load_state_dict_from_url = torch.hub.load_state_dict_from_url
    sys.modules["torchvision.models.utils"] = _utils

import torch

sys.path.insert(0, str(TRAINING_DIR))

def _load_bgr_chw(path: Path, size: int) -> np.ndarray:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        rgb = np.array(Image.open(path).convert("RGB"))
        bgr = np.ascontiguousarray(rgb[:, :, ::-1])
    if bgr.shape[0] != size or bgr.shape[1] != size:
        bgr = cv2.resize(bgr, (size, size), interpolation=cv2.INTER_LINEAR)
    return np.ascontiguousarray(bgr.transpose(2, 0, 1))

_detectors: dict[str, "CrackDetector"] = {}

def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size

def choose_detector(path: Path) -> str:
    name, _ = classify_scene_cv(path)
    return name

def _context_from_mask(image_path: Path, pred: np.ndarray) -> dict:
    h, w = pred.shape
    crack_px = int(pred.sum())
    total = int(pred.size)
    ratio = crack_px / total if total else 0.0
    ys, xs = np.where(pred)
    bbox = None
    if len(xs):
        bbox = {
            "x1": int(xs.min()),
            "y1": int(ys.min()),
            "x2": int(xs.max()),
            "y2": int(ys.max()),
        }
    return {
        "image_path": str(image_path),
        "image_name": image_path.name,
        "width": w,
        "height": h,
        "crack_pixels": crack_px,
        "crack_ratio": round(ratio, 6),
        "has_crack": ratio >= 0.001,
        "bbox": bbox,
    }

_OVERLAY_LANG = "vi"

def set_overlay_lang(lang: str | None) -> None:
    global _OVERLAY_LANG
    _OVERLAY_LANG = "en" if str(lang or "").lower().startswith("en") else "vi"

def _attach_overlay(path: Path, pred: np.ndarray, detector_name: str) -> dict:
    ctx = _context_from_mask(path, pred)
    ctx["detector"] = detector_name
    ctx["scene_kind"] = "hientruong" if detector_name == "lcw" else "cancanh"
    overlay = save_overlay(path, pred, ctx.get("bbox"), lang=_OVERLAY_LANG)
    ctx["overlay_path"] = overlay["path"]
    ctx["overlay_kind"] = overlay["overlay_kind"]
    ctx["overlay_recall"] = overlay.get("recall")
    ctx["overlay_precision"] = overlay.get("precision")
    ctx["overlay_f1"] = overlay.get("f1")
    ctx["overlay_iou"] = overlay.get("iou")
    ctx["overlay_tp"] = overlay.get("tp")
    ctx["overlay_fp"] = overlay.get("fp")
    ctx["overlay_fn"] = overlay.get("fn")
    ctx["overlay_quality"] = overlay.get("quality") or ""
    ctx["overlay_quality_vi"] = overlay.get("quality_vi") or ""
    ctx["overlay_quality_en"] = overlay.get("quality_en") or ""
    ctx["overlay_lang"] = overlay.get("overlay_lang") or _OVERLAY_LANG
    ctx["panel_path"] = overlay.get("panel_path") or ""
    ctx["instances"] = overlay.get("instances") or []
    ctx["boxes_path"] = overlay.get("boxes_path") or ""
    ctx["image_w"] = overlay.get("image_w")
    ctx["image_h"] = overlay.get("image_h")
    ctx["panel_layout"] = overlay.get("panel_layout") or {}
    return ctx

class CrackDetector:
    def __init__(self, weights: Path = CONGLOMERATE_WEIGHTS, name: str = "conglomerate"):
        self.name = name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = torch.load(str(weights), map_location=self.device, weights_only=False)
        self.model.to(self.device)
        self.model.eval()
        if self.device.type == "cuda":
            torch.backends.cudnn.benchmark = True

    def analyze(self, image_path: Path) -> dict:
        return self.analyze_many([image_path])[0]

    def analyze_many(self, image_paths: list[Path]) -> list[dict]:
        paths = [Path(p) for p in image_paths]
        out: list[dict] = []
        workers = min(POST_WORKERS, max(1, len(paths)))
        for start in range(0, len(paths), DETECT_BATCH):
            chunk = paths[start : start + DETECT_BATCH]
            tensors = [
                torch.from_numpy(_load_bgr_chw(p, INPUT_SIZE)).float() for p in chunk
            ]
            x = torch.stack(tensors).to(self.device, non_blocking=self.device.type == "cuda")
            with torch.inference_mode():
                logits = self.model(x)
                if isinstance(logits, dict):
                    logits = logits["out"]
                masks = (torch.argmax(logits, dim=1).cpu().numpy() == 1)
            pairs = list(zip(chunk, masks))
            if len(pairs) == 1:
                out.append(_attach_overlay(pairs[0][0], pairs[0][1], self.name))
            else:
                with ThreadPoolExecutor(max_workers=min(workers, len(pairs))) as pool:
                    futures = [
                        pool.submit(_attach_overlay, path, pred, self.name)
                        for path, pred in pairs
                    ]
                    out.extend(f.result() for f in futures)
        return out

    def close(self) -> None:
        if getattr(self, "model", None) is not None:
            del self.model
            self.model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def get_detector(name: str = "conglomerate") -> CrackDetector:
    if name not in WEIGHTS:
        raise ValueError(f"Unknown detector: {name}")
    det = _detectors.get(name)
    if det is None or getattr(det, "model", None) is None:
        _detectors[name] = CrackDetector(WEIGHTS[name], name=name)
    return _detectors[name]

def release_detector(name: str | None = None) -> None:
    global _detectors
    if name:
        det = _detectors.pop(name, None)
        if det is not None:
            det.close()
        return
    for det in _detectors.values():
        det.close()
    _detectors = {}

def _route_paths(paths: list[Path]) -> tuple[dict[Path, str], dict[Path, str]]:
    first: dict[Path, str] = {}
    reasons: dict[Path, str] = {}
    if VLM_ROUTE:
        from .ollama_client import classify_scene

        for path in paths:
            name, why = classify_scene(path)
            first[path] = name
            reasons[path] = why
        return first, reasons

    def _one(path: Path) -> tuple[Path, str, str]:
        name, why = classify_scene_cv(path)
        return path, name, why

    workers = min(POST_WORKERS, max(1, len(paths)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for path, name, why in pool.map(_one, paths):
            first[path] = name
            reasons[path] = why
    return first, reasons

def analyze_routed(image_paths: list[Path]) -> list[dict]:
    paths = [Path(p) for p in image_paths]
    first, reasons = _route_paths(paths)
    cong = [p for p in paths if first[p] == "conglomerate"]
    lcw = [p for p in paths if first[p] == "lcw"]
    by_path: dict[str, dict] = {}

    if cong:
        for ctx in get_detector("conglomerate").analyze_many(cong):
            by_path[ctx["image_path"]] = ctx
        if LCW_RETRY:
            retry = [
                Path(ctx["image_path"])
                for ctx in by_path.values()
                if not ctx.get("has_crack")
            ]
            lcw.extend(p for p in retry if p not in lcw)
        if not KEEP_MODELS:
            release_detector("conglomerate")

    if lcw:
        for ctx in get_detector("lcw").analyze_many(lcw):
            prev = by_path.get(ctx["image_path"])
            if prev and prev.get("has_crack") and not ctx.get("has_crack"):
                continue
            if prev and prev.get("has_crack") and ctx.get("has_crack"):
                ctx["detector"] = f"lcw+fallback(from {prev['detector']})"
            by_path[ctx["image_path"]] = ctx
        if not KEEP_MODELS:
            release_detector("lcw")

    ordered = []
    for path in paths:
        ctx = by_path[str(path)]
        ctx["scene_reason"] = reasons.get(path, "")
        if first.get(path) == "lcw":
            ctx["scene_kind"] = "hientruong"
        else:
            ctx["scene_kind"] = "cancanh"
        ordered.append(ctx)
    return ordered
