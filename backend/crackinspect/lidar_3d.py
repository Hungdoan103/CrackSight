from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

from .config import (
    LIDAR_3D_GGUF,
    LIDAR_3D_MMPROJ,
    LIDAR_3D_MODEL_DIR,
    LIDAR_3D_REPO,
    LIDAR_DATA_ROOT,
    LIDAR_SCENE_DIR,
    LLAMA_SERVER_URL,
)
from .las_viewer import _file_center, load_points

THREEJS_SYSTEM = (
    "You are a Three.js scene coder. "
    "Use only the Three.js core ES module from "
    "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.module.min.js. "
    "Do not import addons or legacy examples/js paths; "
    "implement orbit-like camera controls inside the HTML. "
    "Return one self-contained HTML document only (no markdown fences, no reasoning)."
)

DEFAULT_PROMPT = (
    "Create one SHORT self-contained HTML Three.js scene (<350 lines). "
    "Y-up. Dark navy #07101c. "
    "Draw: green Points canopy (few hundred pts), yellow Line wires, orange Line powerline, dark road Plane. "
    "HUD top-left + buttons Reset/Top/Hide. Orbit left-drag, pan right-drag, wheel zoom. "
    "Finish the full HTML including </html>. No markdown."
)

LAYER_RGB = {
    "tree": (34, 180, 80),
    "wires": (230, 190, 40),
    "powerline": (230, 90, 40),
    "default": (120, 170, 220),
}

def model_status() -> dict:
    server_ok = False
    try:
        with urllib.request.urlopen(f"{LLAMA_SERVER_URL.rstrip('/')}/health", timeout=2) as resp:
            server_ok = resp.status == 200
    except Exception:
        server_ok = False
    return {
        "repo": LIDAR_3D_REPO,
        "model_dir": str(LIDAR_3D_MODEL_DIR),
        "gguf": LIDAR_3D_GGUF.exists(),
        "gguf_path": str(LIDAR_3D_GGUF),
        "mmproj": LIDAR_3D_MMPROJ.exists(),
        "mmproj_path": str(LIDAR_3D_MMPROJ),
        "llama_server": LLAMA_SERVER_URL,
        "llama_server_up": server_ok,
        "role": "threejs-3d-coder",
        "note": (
            "Generates Three.js HTML from text/image. "
            "Not a LiDAR point-cloud detector. Prefer /lidar/build for real points."
        ),
    }

def _extract_html(text: str) -> str:
    raw = (text or "").strip()
    fence = re.search(r"```(?:html)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    start = raw.lower().find("<!doctype html")
    if start < 0:
        start = raw.lower().find("<html")
    if start >= 0:
        raw = raw[start:]
    end = raw.lower().rfind("</html>")
    if end >= 0:
        raw = raw[: end + len("</html>")]
    return raw.strip()

def _message_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            elif isinstance(item, str):
                parts.append(item)
        content = "\n".join(parts)
    text = (content or "").strip()
    if text:
        return text
    return str(message.get("reasoning_content") or message.get("reasoning") or "").strip()

def _image_data_url(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    suffix = path.suffix.lower().lstrip(".") or "jpeg"
    mime = "image/png" if suffix == "png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"

def render_birdeye_preview(
    names: list[str] | None = None,
    *,
    max_points: int = 80_000,
    size: int = 768,
    out_name: str = "lidar_birdeye",
) -> dict:
    root = LIDAR_DATA_ROOT
    if not root.is_dir():
        raise FileNotFoundError(f"LiDAR data root missing: {root}")
    if names:
        paths = [root / Path(n).name for n in names]
    else:
        paths = sorted(root.glob("*.las"))
        key = root.name
        matched = [p for p in paths if key in p.stem]
        if matched:
            paths = matched
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing LAS: " + ", ".join(missing))

    centers = np.array([_file_center(p) for p in paths], dtype=np.float64)
    origin = tuple(float(v) for v in centers.mean(axis=0))
    per = max(3_000, max_points // max(1, len(paths)))
    clouds = [load_points(p, max_points=per, origin=origin) for p in paths]

    xs = np.concatenate([c["xyz"][:, 0] for c in clouds])
    ys = np.concatenate([c["xyz"][:, 1] for c in clouds])
    pad = 2.0
    xmin, xmax = float(xs.min()) - pad, float(xs.max()) + pad
    ymin, ymax = float(ys.min()) - pad, float(ys.max()) + pad
    span = max(xmax - xmin, ymax - ymin, 1.0)
    cx, cy = (xmin + xmax) * 0.5, (ymin + ymax) * 0.5
    xmin, xmax = cx - span * 0.5, cx + span * 0.5
    ymin, ymax = cy - span * 0.5, cy + span * 0.5

    canvas = np.zeros((size, size, 3), dtype=np.float32)
    weight = np.zeros((size, size), dtype=np.float32)
    for cloud in clouds:
        rgb = np.array(LAYER_RGB.get(cloud["layer"], LAYER_RGB["default"]), dtype=np.float32)
        xyz = cloud["xyz"]
        u = ((xyz[:, 0] - xmin) / (xmax - xmin) * (size - 1)).astype(np.int32)
        v = ((ymax - xyz[:, 1]) / (ymax - ymin) * (size - 1)).astype(np.int32)
        ok = (u >= 0) & (u < size) & (v >= 0) & (v < size)
        u, v = u[ok], v[ok]
        for ui, vi in zip(u.tolist(), v.tolist()):
            canvas[vi, ui] += rgb
            weight[vi, ui] += 1.0
    mask = weight > 0
    canvas[mask] /= weight[mask, None]
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = (11, 18, 32)  # dark navy
    img[mask] = np.clip(canvas[mask], 0, 255).astype(np.uint8)

    LIDAR_SCENE_DIR.mkdir(parents=True, exist_ok=True)
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in out_name)[:60]
    out = LIDAR_SCENE_DIR / f"{stem}.jpg"
    Image.fromarray(img, mode="RGB").save(out, quality=92)
    return {
        "image": str(out),
        "image_name": out.name,
        "origin": list(origin),
        "layers": [
            {"name": c["name"], "layer": c["layer"], "count": c["count"], "count_total": c["count_total"]}
            for c in clouds
        ],
        "extent_m": {"x": xmax - xmin, "y": ymax - ymin},
    }

def build_prompt_from_layers(layers: list[dict], extent_m: dict | None = None) -> str:
    lines = []
    for row in layers:
        lines.append(
            f"- {row['layer']}: file {row['name']}, "
            f"{row['count']:,} sampled / {row['count_total']:,} total points"
        )
    ext = ""
    if extent_m:
        ext = f" Corridor extent about {extent_m.get('x', 0):.0f}m x {extent_m.get('y', 0):.0f}m."
    return (
        DEFAULT_PROMPT
        + ext
        + " Match these real LiDAR layers from site 223582:\n"
        + "\n".join(lines)
        + "\nUse the same colors: tree=green, wires=yellow, powerline=orange."
    )

def generate_scene_via_llama_server(
    prompt: str,
    image_path: Path | None = None,
    *,
    temperature: float = 0.55,
    max_tokens: int = 6144,
    out_stem: str = "qwen3d_scene",
) -> dict:
    if not LIDAR_3D_GGUF.exists():
        raise FileNotFoundError(
            f"Missing {LIDAR_3D_GGUF}. Run scripts/download_qwen35_3d_coder.ps1 first."
        )
    user_content: str | list[dict]
    if image_path is not None:
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        user_content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": _image_data_url(path)},
            },
        ]
    else:
        user_content = prompt
    if isinstance(user_content, str):
        user_content = "/no_think\n" + user_content
    elif isinstance(user_content, list) and user_content and user_content[0].get("type") == "text":
        user_content = [
            {"type": "text", "text": "/no_think\n" + str(user_content[0].get("text") or "")},
            *user_content[1:],
        ]
    payload = {
        "model": "Qwen3.5-4B-3D-Coder",
        "temperature": temperature,
        "top_p": 0.95,
        "top_k": 20,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": THREEJS_SYSTEM},
            {"role": "user", "content": user_content},
        ],
    }
    req = urllib.request.Request(
        f"{LLAMA_SERVER_URL.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach llama-server at {LLAMA_SERVER_URL}. "
            "Start it with the GGUF on E: (see scripts/run_llama_3d_server.ps1)."
        ) from exc
    message = ((data.get("choices") or [{}])[0].get("message") or {})
    text = _message_text(message)
    html = _extract_html(text)
    if not html or "<html" not in html.lower():
        raise RuntimeError(
            "3D-Coder returned empty/invalid HTML. "
            f"Raw head: {(text or '')[:240]!r}"
        )
    if "</html>" not in html.lower():
        raise RuntimeError(
            "3D-Coder HTML was truncated (missing </html>). "
            "Increase max_tokens or use /lidar/build for real points."
        )
    if html.count("<script") != html.count("</script>"):
        raise RuntimeError("3D-Coder HTML truncated inside <script>; refusing to save blank scene.")
    LIDAR_SCENE_DIR.mkdir(parents=True, exist_ok=True)
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in out_stem)[:60]
    out = LIDAR_SCENE_DIR / f"{stem}.html"
    out.write_text(html, encoding="utf-8")
    return {
        "html": str(out),
        "html_name": out.name,
        "html_path": str(out),
        "bytes": out.stat().st_size,
        "model": LIDAR_3D_REPO,
        "source": "llama-server",
        "view_url": f"/lidar/view/{out.name}",
        "used_image": str(image_path) if image_path else None,
    }

def generate_from_las(
    names: list[str] | None = None,
    *,
    prompt: str | None = None,
    max_points: int = 80_000,
    fallback_real: bool = True,
) -> dict:
    from .las_viewer import build_voxel_viewer

    preview = render_birdeye_preview(names, max_points=max_points, out_name="lidar_birdeye_223582")
    text = prompt or build_prompt_from_layers(preview["layers"], preview.get("extent_m"))
    try:
        scene = generate_scene_via_llama_server(
            text,
            Path(preview["image"]),
            out_stem="qwen3d_223582",
            max_tokens=8192,
        )
        scene["preview"] = preview
        scene["prompt"] = text
        return scene
    except Exception as exc:
        if not fallback_real:
            raise
        real = build_voxel_viewer(
            names,
            max_points=max(max_points, 60_000),
            out_name="qwen3d_223582_voxel",
        )
        real["preview"] = preview
        real["prompt"] = text
        real["fallback"] = "voxel-from-las"
        real["qwen_error"] = str(exc)
        real["model"] = LIDAR_3D_REPO
        real["note"] = (
            "Qwen HTML failed or invented bad coords; served real-LAS voxel viewer instead."
        )
        return real
