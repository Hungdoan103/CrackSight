from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import OVERLAY_DIR, PROJECT_ROOT

CRACK_COLOR = (255, 40, 40)
BOX_COLOR = (255, 220, 0)
ALPHA = 0.55
PANEL_CELL = 512
PANEL_GAP = 8
PANEL_CAP = 32
_MASK_DIRS: list[Path] | None = None

def overlay_path_for(image_path: Path) -> Path:
    return OVERLAY_DIR / f"{Path(image_path).stem}_crack.jpg"

def boxes_path_for(image_path: Path) -> Path:
    return OVERLAY_DIR / f"{Path(image_path).stem}_boxes.jpg"

def panel_path_for(image_path: Path) -> Path:
    return OVERLAY_DIR / f"{Path(image_path).stem}_panel.jpg"

def pixel_metrics(gt: np.ndarray, pred: np.ndarray) -> dict:
    g = gt.astype(bool)
    p = pred.astype(bool)
    tp = int((g & p).sum())
    fp = int(((~g) & p).sum())
    fn = int((g & (~p)).sum())
    tn = int(((~g) & (~p)).sum())
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "recall": round(rec, 4),
        "precision": round(prec, 4),
        "f1": round(f1, 4),
        "iou": round(iou, 4),
    }

def assess_quality(m: dict, lang: str = "vi") -> str:
    rec = float(m.get("recall") or 0)
    prec = float(m.get("precision") or 0)
    f1 = float(m.get("f1") or 0)
    iou = float(m.get("iou") or 0)
    tp, fp, fn = m.get("tp", 0), m.get("fp", 0), m.get("fn", 0)
    en = str(lang).lower().startswith("en")
    if en:
        if rec >= 0.8:
            rec_txt = "High recall: few missed true cracks (low FN)"
        elif rec >= 0.4:
            rec_txt = "Medium recall: some true cracks still missed"
        else:
            rec_txt = "Low recall: many crack pixels missed"
        if prec >= 0.6:
            prec_txt = "Decent precision: little over-paint"
        elif prec >= 0.25:
            prec_txt = "Low precision: many false pixels (FP) — LCW often paints wider than labels"
        else:
            prec_txt = "Very low precision: prediction mask much wider than labels"
        return (
            f"{rec_txt}. {prec_txt}. "
            f"Overall F1={f1:.2f}, IoU={iou:.2f} (TP {tp}, FP {fp}, FN {fn}). "
            "Do not judge from precision alone."
        )
    if rec >= 0.8:
        rec_txt = "Recall cao: ít bỏ sót vết thật (FN ít)"
    elif rec >= 0.4:
        rec_txt = "Recall trung bình: còn bỏ sót một phần"
    else:
        rec_txt = "Recall thấp: bỏ sót nhiều pixel nứt"
    if prec >= 0.6:
        prec_txt = "Precision khá: ít tô thừa"
    elif prec >= 0.25:
        prec_txt = "Precision thấp: nhiều pixel thừa (FP) — LCW hay tô rộng hơn nhãn"
    else:
        prec_txt = "Precision rất thấp: mask dự đoán rộng hơn nhãn nhiều"
    return (
        f"{rec_txt}. {prec_txt}. "
        f"Tổng thể F1={f1:.2f}, IoU={iou:.2f} (TP {tp}, FP {fp}, FN {fn}). "
        "Không kết luận chỉ từ precision."
    )

def _overlay_copy(lang: str = "vi") -> dict[str, str]:
    en = str(lang).lower().startswith("en")
    if en:
        return {
            "boxes": "DeepInspect — crack pixels (red) + instance boxes on the mask",
            "boxes_file": "DeepInspect — model crack pixels (red); boxes = mask regions",
            "tpfpfn": "TP green / FP red / FN yellow   rec={rec:.2f} prec={prec:.2f} F1={f1:.2f} IoU={iou:.2f}",
            "pred_only": "Prediction (red) — no ground-truth label, so the 4-panel view is unavailable",
            "cell_original": "Original",
            "cell_gt": "Ground truth (green)",
            "cell_pred": "Prediction (red) + box",
            "cell_err": "TP/FP/FN  rec={rec:.2f} prec={prec:.2f} F1={f1:.2f}",
        }
    return {
        "boxes": "DeepInspect — pixel nứt (đỏ) + khung từng vết trên mask",
        "boxes_file": "DeepInspect — pixel nứt (đỏ) từ model, khung = từng vùng trên mask",
        "tpfpfn": "TP xanh / FP đỏ / FN vàng   rec={rec:.2f} prec={prec:.2f} F1={f1:.2f} IoU={iou:.2f}",
        "pred_only": "Dự đoán (đỏ) — không có nhãn gốc nên không vẽ được ô 4",
        "cell_original": "Ảnh gốc",
        "cell_gt": "Nhãn gốc (xanh)",
        "cell_pred": "Dự đoán (đỏ) + khung",
        "cell_err": "TP/FP/FN  rec={rec:.2f} prec={prec:.2f} F1={f1:.2f}",
    }

def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def save_boxes_image(
    image_path: Path,
    instances: list[dict],
    base: np.ndarray | None = None,
    caption: str | None = None,
    lang: str = "vi",
) -> str:
    if caption is None:
        caption = _overlay_copy(lang)["boxes"]
    image_path = Path(image_path)
    dest = boxes_path_for(image_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if base is None:
        img = Image.open(image_path).convert("RGB")
    else:
        img = Image.fromarray(base)
    draw = ImageDraw.Draw(img)
    ow, oh = img.size
    width = max(3, min(ow, oh) // 160)
    font = _font(max(16, min(ow, oh) // 28))
    for inst in instances:
        box = inst["bbox"]
        x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
        draw.rectangle([x1, y1, x2, y2], outline=(220, 38, 38), width=width)
        label = f"crack {inst.get('score', 0):.2f}"
        tx, ty = x1, max(0, y1 - int(font.size * 1.3))
        tb = draw.textbbox((tx, ty), label, font=font)
        draw.rectangle(tb, fill=(220, 38, 38))
        draw.text((tx, ty), label, fill=(255, 255, 255), font=font)
    vis = _caption(np.array(img), caption)
    Image.fromarray(vis).save(dest, quality=92)
    return str(dest)

def _mask_dirs() -> list[Path]:
    global _MASK_DIRS
    if _MASK_DIRS is not None:
        return _MASK_DIRS
    root = PROJECT_ROOT / "Datasets"
    cong = root / "Conglomerate _Crack" / "Conglomerate _Crack_datasetset_2764"
    cong2 = (
        root
        / "Concrete Crack Conglomerate Dataset"
        / "Concrete Crack Conglomerate Dataset"
        / "Conglomerate Concrete Crack Detection 1"
    )
    lcw = (
        root
        / "Labeled Cracks in the Wild (LCW) Dataset"
        / "16624672"
        / "LCW Concrete Crack Detection"
        / "LCW Concrete Crack Detection"
    )
    dirs: list[Path] = []
    for base in (cong, cong2):
        for split in ("Test", "Train"):
            dirs.append(base / split / "masks")
    for variant in ("512x512", "512x512_dilated_no_blanks", "original", "original_dilated"):
        for split in ("Test", "Train"):
            dirs.append(lcw / variant / split / "masks")
    _MASK_DIRS = [d for d in dirs if d.is_dir()]
    return _MASK_DIRS

def _sibling_mask(image_path: Path) -> Path | None:
    if image_path.parent.name.lower() != "images":
        return None
    masks_dir = image_path.parent.parent / "masks"
    if not masks_dir.is_dir():
        return None
    for ext in (image_path.suffix, ".png", ".jpg", ".jpeg", ".PNG", ".JPG"):
        cand = masks_dir / f"{image_path.stem}{ext}"
        if cand.exists():
            return cand
    return None

def find_gt_mask(image_path: Path) -> Path | None:
    image_path = Path(image_path)
    sibling = _sibling_mask(image_path)
    if sibling:
        return sibling
    from .exifMeta import annotated_gt_path

    annotated = annotated_gt_path(image_path)
    if annotated:
        return annotated
    stems: list[str] = []
    raw = image_path.stem
    for stem in (raw, raw[:-5] if raw.endswith("_meta") else "", re.sub(r"_\d+$", "", raw)):
        if stem and stem not in stems:
            stems.append(stem)
    hits: list[Path] = []
    for stem in stems:
        for folder in _mask_dirs():
            for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG"):
                cand = folder / f"{stem}{ext}"
                if cand.exists():
                    hits.append(cand)
                    break
    if not hits:
        return None

    def _crack_n(p: Path) -> int:
        try:
            return int((np.array(Image.open(p).convert("L")) > 127).sum())
        except Exception:
            return 0

    scored = [(p, _crack_n(p)) for p in hits]
    labeled = [row for row in scored if row[1] > 0]
    if labeled:
        scored = labeled
    if len(scored) == 1:
        return scored[0][0]
    with Image.open(image_path) as im:
        iw, ih = im.size

    def _rank(row: tuple[Path, int]) -> tuple:
        p, n = row
        parts = {part.lower() for part in p.parts}
        text = "\\".join(p.parts).lower()
        empty = 0 if n > 0 else 1
        dilated = 1 if "dilated" in text else 0
        is_512 = 0 if "512x512" in text else 1
        split = 0 if "test" in parts else 1
        return (empty, dilated, is_512, split, -n)

    scored.sort(key=_rank)
    return scored[0][0]

def _dilate(mask: np.ndarray, radius: int = 1) -> np.ndarray:
    if radius <= 0 or not mask.any():
        return mask
    img = Image.fromarray((mask.astype(np.uint8) * 255))
    size = radius * 2 + 1
    return np.array(img.filter(ImageFilter.MaxFilter(size))) > 0

def _resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    ow, oh = size
    if mask.shape == (oh, ow):
        return mask.astype(bool)
    return (
        np.array(Image.fromarray(mask.astype(np.uint8) * 255).resize((ow, oh), Image.NEAREST))
        > 0
    )

def _load_gt(mask_path: Path, size: tuple[int, int]) -> np.ndarray:
    gray = np.array(Image.open(mask_path).convert("L").resize(size, Image.NEAREST))
    return gray > 127

def _tint(rgb: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], alpha: float) -> np.ndarray:
    out = rgb.astype(np.float32)
    tint = np.zeros_like(out)
    tint[mask] = color
    out[mask] = (1 - alpha) * out[mask] + alpha * tint[mask]
    return np.clip(out, 0, 255).astype(np.uint8)

def error_map(rgb: np.ndarray, gt: np.ndarray, pred: np.ndarray) -> np.ndarray:
    out = rgb.astype(np.float32)
    for mask, color, alpha in (
        (gt & pred, (0, 220, 80), 0.55),
        ((~gt) & pred, (255, 50, 50), 0.60),
        (gt & (~pred), (255, 220, 0), 0.60),
    ):
        tint = np.zeros_like(out)
        tint[mask] = color
        out[mask] = (1 - alpha) * out[mask] + alpha * tint[mask]
    return np.clip(out, 0, 255).astype(np.uint8)

def _caption(img: np.ndarray, text: str) -> np.ndarray:
    im = Image.fromarray(img)
    size = 18 if im.width >= 720 else 14 if im.width >= 480 else 11
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except Exception:
        font = ImageFont.load_default()
    dummy = ImageDraw.Draw(im)
    max_w = max(40, im.width - 20)
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if dummy.textbbox((0, 0), trial, font=font)[2] <= max_w or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    line_h = size + 8
    bar_h = 10 + line_h * max(1, len(lines))
    bar = Image.new("RGB", (im.width, bar_h), (20, 20, 20))
    draw = ImageDraw.Draw(bar)
    y = 6
    for line in lines:
        draw.text((10, y), line, fill=(255, 255, 255), font=font)
        y += line_h
    canvas = Image.new("RGB", (im.width, im.height + bar_h), (20, 20, 20))
    canvas.paste(bar, (0, 0))
    canvas.paste(im, (0, bar_h))
    return np.array(canvas)

def render_prediction(
    image_path: Path,
    mask: np.ndarray,
    bbox: dict | None = None,
    rgb: np.ndarray | None = None,
) -> np.ndarray:
    if rgb is None:
        rgb = np.array(Image.open(image_path).convert("RGB"))
    oh, ow = rgb.shape[:2]
    vis_mask = _resize_mask(_dilate(mask.astype(bool), 1), (ow, oh))
    vis = _tint(rgb, vis_mask, CRACK_COLOR, ALPHA)
    if bbox:
        mh, mw = mask.shape
        sx, sy = ow / mw, oh / mh
        img = Image.fromarray(vis)
        draw = ImageDraw.Draw(img)
        width = max(2, min(ow, oh) // 180)
        draw.rectangle(
            [
                int(bbox["x1"] * sx),
                int(bbox["y1"] * sy),
                int(bbox["x2"] * sx),
                int(bbox["y2"] * sy),
            ],
            outline=BOX_COLOR,
            width=width,
        )
        vis = np.array(img)
    return vis

def render_overlay(image_path: Path, mask: np.ndarray, bbox: dict | None = None) -> np.ndarray:
    return render_prediction(image_path, mask, bbox)

def _draw_boxes(rgb: np.ndarray, instances: list[dict]) -> np.ndarray:
    if not instances:
        return rgb
    img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(img)
    ow, oh = img.size
    width = max(2, min(ow, oh) // 160)
    font = _font(max(14, min(ow, oh) // 32))
    for inst in instances:
        box = inst.get("bbox") or {}
        x1, y1 = int(box.get("x1", 0)), int(box.get("y1", 0))
        x2, y2 = int(box.get("x2", 0)), int(box.get("y2", 0))
        draw.rectangle([x1, y1, x2, y2], outline=(220, 38, 38), width=width)
        label = f"#{inst.get('id', '?')} {float(inst.get('score') or 0):.2f}"
        tx, ty = x1, max(0, y1 - int(font.size * 1.3))
        tb = draw.textbbox((tx, ty), label, font=font)
        draw.rectangle(tb, fill=(220, 38, 38))
        draw.text((tx, ty), label, fill=(255, 255, 255), font=font)
    return np.array(img)

def _cell(rgb: np.ndarray, title: str, side: int = PANEL_CELL, cap: int = PANEL_CAP) -> Image.Image:
    im = Image.fromarray(rgb).resize((side, side), Image.NEAREST)
    bar = Image.new("RGB", (side, cap), (20, 20, 20))
    draw = ImageDraw.Draw(bar)
    font = _font(13)
    draw.text((8, 8), title[:70], fill=(255, 255, 255), font=font)
    canvas = Image.new("RGB", (side, side + cap), (20, 20, 20))
    canvas.paste(bar, (0, 0))
    canvas.paste(im, (0, cap))
    return canvas

def save_eval_panel(
    image_path: Path,
    rgb: np.ndarray,
    gt: np.ndarray,
    pred: np.ndarray,
    metrics: dict,
    instances: list[dict] | None = None,
    lang: str = "vi",
) -> str:
    dest = panel_path_for(image_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rec = float(metrics["recall"])
    prec = float(metrics["precision"])
    f1 = float(metrics["f1"])
    boxes = instances or []
    copy = _overlay_copy(lang)
    cells = [
        _cell(rgb, copy["cell_original"]),
        _cell(_tint(rgb, gt, (0, 220, 80), ALPHA), copy["cell_gt"]),
        _cell(_draw_boxes(_tint(rgb, pred, CRACK_COLOR, ALPHA), boxes), copy["cell_pred"]),
        _cell(
            error_map(rgb, gt, pred),
            copy["cell_err"].format(rec=rec, prec=prec, f1=f1),
        ),
    ]
    w, h = cells[0].size
    grid = Image.new("RGB", (w * 2 + PANEL_GAP, h * 2 + PANEL_GAP), (30, 30, 30))
    grid.paste(cells[0], (0, 0))
    grid.paste(cells[1], (w + PANEL_GAP, 0))
    grid.paste(cells[2], (0, h + PANEL_GAP))
    grid.paste(cells[3], (w + PANEL_GAP, h + PANEL_GAP))
    grid.save(dest, quality=92)
    return str(dest)

def save_overlay(
    image_path: Path,
    mask: np.ndarray,
    bbox: dict | None = None,
    *,
    refine_sift: bool | None = None,
    lang: str = "vi",
) -> dict:
    from .config import DETECT_SIFT
    from .instances import find_instances, refine_instances_sift

    image_path = Path(image_path)
    dest = overlay_path_for(image_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.array(Image.open(image_path).convert("RGB"))
    ow, oh = rgb.shape[1], rgb.shape[0]
    pred = _resize_mask(mask.astype(bool), (ow, oh))
    use_sift = DETECT_SIFT if refine_sift is None else refine_sift
    instances = find_instances(pred)
    if use_sift:
        instances = refine_instances_sift(rgb, instances)
    gt_path = find_gt_mask(image_path)
    copy = _overlay_copy(lang)
    info = {
        "path": str(dest),
        "overlay_kind": "pred",
        "recall": None,
        "precision": None,
        "f1": None,
        "iou": None,
        "tp": None,
        "fp": None,
        "fn": None,
        "quality": "",
        "quality_vi": "",
        "quality_en": "",
        "panel_path": "",
        "image_w": ow,
        "image_h": oh,
        "overlay_lang": "en" if str(lang).lower().startswith("en") else "vi",
        "panel_layout": {"cell": PANEL_CELL, "gap": PANEL_GAP, "caption": PANEL_CAP},
    }

    pred_vis = render_prediction(image_path, mask, bbox=None, rgb=rgb)
    if gt_path:
        gt = _load_gt(gt_path, (ow, oh))
        m = pixel_metrics(gt, pred)
        vis = error_map(rgb, gt, pred)
        vis = _caption(
            vis,
            copy["tpfpfn"].format(
                rec=m["recall"],
                prec=m["precision"],
                f1=m["f1"],
                iou=m["iou"],
            ),
        )
        q_vi = assess_quality(m, "vi")
        q_en = assess_quality(m, "en")
        info.update(
            overlay_kind="tpfpfn",
            **m,
            quality=q_en if str(lang).lower().startswith("en") else q_vi,
            quality_vi=q_vi,
            quality_en=q_en,
        )
        info["panel_path"] = save_eval_panel(image_path, rgb, gt, pred, m, instances, lang=lang)
    else:
        vis = render_prediction(image_path, mask, bbox, rgb=rgb)
        vis = _caption(vis, copy["pred_only"])

    Image.fromarray(vis).save(dest, quality=90)
    info["instances"] = instances
    info["boxes_path"] = save_boxes_image(
        image_path,
        instances,
        base=pred_vis,
        caption=copy["boxes_file"],
        lang=lang,
    )
    return info
