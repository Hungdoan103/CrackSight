from __future__ import annotations

import cv2
import numpy as np

def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return img

def sift_snap_bbox(rgb: np.ndarray, bbox: dict, pad: int = 12) -> tuple[dict, dict]:
    h, w = rgb.shape[:2]
    x1 = int(bbox.get("x1", 0))
    y1 = int(bbox.get("y1", 0))
    x2 = int(bbox.get("x2", x1))
    y2 = int(bbox.get("y2", y1))
    x2 = max(x2, x1 + 1)
    y2 = max(y2, y1 + 1)
    cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
    cx2, cy2 = min(w, x2 + 1 + pad), min(h, y2 + 1 + pad)
    crop = rgb[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return bbox, {"sift_ok": False, "sift_inliers": 0}

    gray_c = _gray(crop)
    std = float(gray_c.std())
    mean = float(gray_c.mean())
    sift = cv2.SIFT_create(nfeatures=600)
    kp1, des1 = sift.detectAndCompute(gray_c, None)
    nkp = 0 if kp1 is None else len(kp1)
    if nkp < 6 and (mean < 35 or std < 10):
        return bbox, {
            "sift_ok": False,
            "sift_inliers": 0,
            "sift_drop": True,
            "sift_reason": "vùng tối/không kết cấu",
        }
    if des1 is None or nkp < 6:
        return bbox, {"sift_ok": False, "sift_inliers": 0}

    bw, bh = x2 - x1 + 1, y2 - y1 + 1
    sx1 = max(0, x1 - max(80, bw * 3))
    sy1 = max(0, y1 - max(80, bh * 3))
    sx2 = min(w, x2 + 1 + max(80, bw * 3))
    sy2 = min(h, y2 + 1 + max(80, bh * 3))
    search = rgb[sy1:sy2, sx1:sx2]
    kp2, des2 = sift.detectAndCompute(_gray(search), None)
    if des2 is None or len(kp2) < 8:
        return bbox, {"sift_ok": False, "sift_inliers": 0}

    matcher = cv2.BFMatcher(cv2.NORM_L2)
    try:
        pairs = matcher.knnMatch(des1, des2, k=2)
    except cv2.error:
        return bbox, {"sift_ok": False, "sift_inliers": 0}

    good = []
    for pair in pairs:
        if len(pair) < 2:
            continue
        first, second = pair
        if first.distance < 0.75 * second.distance:
            good.append(first)
    if len(good) < 6:
        return bbox, {"sift_ok": False, "sift_inliers": len(good)}

    src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    homography, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if homography is None or mask is None:
        return bbox, {"sift_ok": False, "sift_inliers": len(good)}
    inliers = int(mask.ravel().sum())
    if inliers < 6:
        return bbox, {"sift_ok": False, "sift_inliers": inliers}

    inner = np.float32(
        [
            [x1 - cx1, y1 - cy1],
            [x2 + 1 - cx1, y1 - cy1],
            [x2 + 1 - cx1, y2 + 1 - cy1],
            [x1 - cx1, y2 + 1 - cy1],
        ]
    ).reshape(-1, 1, 2)
    proj = cv2.perspectiveTransform(inner, homography)
    xs = proj[:, 0, 0] + sx1
    ys = proj[:, 0, 1] + sy1
    nx1 = int(np.clip(np.floor(xs.min()), 0, w - 1))
    ny1 = int(np.clip(np.floor(ys.min()), 0, h - 1))
    nx2 = int(np.clip(np.ceil(xs.max()), 0, w - 1))
    ny2 = int(np.clip(np.ceil(ys.max()), 0, h - 1))
    if nx2 <= nx1 or ny2 <= ny1:
        return bbox, {"sift_ok": False, "sift_inliers": inliers}
    return {"x1": nx1, "y1": ny1, "x2": nx2, "y2": ny2}, {"sift_ok": True, "sift_inliers": inliers}

def refine_instances_sift(rgb: np.ndarray, instances: list[dict]) -> list[dict]:
    out: list[dict] = []
    for inst in instances:
        box = inst.get("bbox") or {}
        if not box:
            out.append(dict(inst))
            continue
        new_box, meta = sift_snap_bbox(np.asarray(rgb), box)
        if meta.get("sift_drop"):
            continue
        row = dict(inst)
        row["bbox"] = new_box
        row["sift_ok"] = bool(meta.get("sift_ok"))
        row["sift_inliers"] = int(meta.get("sift_inliers") or 0)
        bw = max(1, new_box["x2"] - new_box["x1"] + 1)
        bh = max(1, new_box["y2"] - new_box["y1"] + 1)
        row["length_px"] = float(max(bw, bh))
        if row.get("pixels"):
            row["width_avg_px"] = round(float(row["pixels"]) / row["length_px"], 2)
        row["axis"] = "ngang" if bw >= bh else "dọc"
        out.append(row)
    return out

def find_instances(mask: np.ndarray, min_pixels: int = 80) -> list[dict]:
    binary = (np.asarray(mask) > 0).astype(np.uint8)
    if not binary.any():
        return []
    num, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    raw: list[dict] = []
    for i in range(1, num):
        pixels = int(stats[i, cv2.CC_STAT_AREA])
        if pixels < min_pixels:
            continue
        x, y = int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP])
        w, h = int(stats[i, cv2.CC_STAT_WIDTH]), int(stats[i, cv2.CC_STAT_HEIGHT])
        length_px = float(max(w, h, 1))
        width_avg_px = round(pixels / length_px, 2)
        raw.append(
            {
                "bbox": {"x1": x, "y1": y, "x2": x + w - 1, "y2": y + h - 1},
                "pixels": pixels,
                "length_px": length_px,
                "width_avg_px": width_avg_px,
                "axis": "ngang" if w >= h else "dọc",
            }
        )
    raw.sort(key=lambda r: r["pixels"], reverse=True)
    max_px = raw[0]["pixels"] if raw else 1
    out = []
    for i, item in enumerate(raw, 1):
        score = min(0.99, 0.55 + 0.44 * (item["pixels"] / max_px))
        item["id"] = i
        item["score"] = round(float(score), 2)
        out.append(item)
    return out

def apply_scale(instances: list[dict], rec: dict) -> list[dict]:
    gsd = rec.get("gsd_mm_per_px")
    gsd = float(gsd) if gsd not in (None, "") else None
    scaled = []
    for item in instances:
        row = dict(item)
        if gsd:
            row["length_mm"] = round(row["length_px"] * gsd, 1)
            row["width_avg_mm"] = round(row["width_avg_px"] * gsd, 2)
        scaled.append(row)
    if (
        len(scaled) == 1
        and rec.get("length_mm") is not None
        and rec.get("width_avg_mm") is not None
    ):
        scaled[0]["length_mm"] = float(rec["length_mm"])
        scaled[0]["width_avg_mm"] = float(rec["width_avg_mm"])
        if rec.get("width_max_mm") is not None:
            scaled[0]["width_max_mm"] = float(rec["width_max_mm"])
    for row in scaled:
        row["level"] = _level(row)
        row["action"] = _action(row["level"])
    return scaled

def _level(row: dict) -> str:
    width = row.get("width_avg_mm")
    if width is None:
        if row.get("score", 0) >= 0.9:
            return "cao"
        if row.get("score", 0) >= 0.75:
            return "trung bình"
        return "nhẹ"
    if width >= 3.0:
        return "cao"
    if width >= 1.5:
        return "trung bình"
    return "nhẹ"

def _action(level: str) -> str:
    if level == "cao":
        return "kiểm tra hiện trường ưu tiên"
    if level == "trung bình":
        return "theo dõi định kỳ"
    return "theo dõi định kỳ"
