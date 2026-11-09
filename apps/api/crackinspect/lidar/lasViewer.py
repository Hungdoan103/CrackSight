from __future__ import annotations

import json
from pathlib import Path

import laspy
import numpy as np

from ..core.config import LIDAR_DATA_ROOT, LIDAR_SCENE_DIR

LAYER_COLORS = {
    "tree": (0.22, 0.72, 0.35),
    "wires": (0.95, 0.82, 0.2),
    "powerline": (0.95, 0.35, 0.15),
    "default": (0.55, 0.75, 0.95),
}

def list_las_files(root: Path | None = None) -> list[dict]:
    base = Path(root or LIDAR_DATA_ROOT)
    if not base.is_dir():
        return []
    items = []
    for path in sorted(base.glob("*.las")):
        try:
            las = laspy.read(path)
            n = int(len(las.points))
        except Exception:
            n = -1
        items.append(
            {
                "name": path.name,
                "path": str(path),
                "bytes": path.stat().st_size,
                "points": n,
                "layer": _layer_of(path.name),
            }
        )
    return items

def _layer_of(name: str) -> str:
    lower = name.lower()
    for key in ("tree", "wires", "powerline"):
        if lower.startswith(key):
            return key
    return "default"

def _sample_indices(n: int, max_points: int, rng: np.random.Generator) -> np.ndarray:
    if n <= max_points:
        return np.arange(n, dtype=np.int64)
    return np.sort(rng.choice(n, size=max_points, replace=False))

def _file_center(path: Path) -> tuple[float, float, float]:
    with laspy.open(path) as reader:
        mins = np.asarray(reader.header.mins, dtype=np.float64)
        maxs = np.asarray(reader.header.maxs, dtype=np.float64)
    mid = (mins + maxs) * 0.5
    return float(mid[0]), float(mid[1]), float(mid[2])

def load_points(
    path: Path,
    *,
    max_points: int = 200_000,
    seed: int = 0,
    origin: tuple[float, float, float] | None = None,
) -> dict:
    las = laspy.read(path)
    n = len(las.points)
    rng = np.random.default_rng(seed)
    idx = _sample_indices(n, max_points, rng)
    x = np.asarray(las.x, dtype=np.float64)[idx]
    y = np.asarray(las.y, dtype=np.float64)[idx]
    z = np.asarray(las.z, dtype=np.float64)[idx]
    intensity = None
    if "intensity" in las.point_format.dimension_names:
        intensity = np.asarray(las.intensity, dtype=np.float32)[idx]
    if origin is None:
        ox, oy, oz = float(x.mean()), float(y.mean()), float(z.mean())
    else:
        ox, oy, oz = origin
    xyz = np.column_stack((x - ox, y - oy, z - oz)).astype(np.float32)
    layer = _layer_of(path.name)
    base = LAYER_COLORS.get(layer, LAYER_COLORS["default"])
    if intensity is not None and intensity.max() > intensity.min():
        t = (intensity - intensity.min()) / (intensity.max() - intensity.min() + 1e-6)
        colors = np.column_stack(
            (
                base[0] * (0.45 + 0.55 * t),
                base[1] * (0.45 + 0.55 * t),
                base[2] * (0.45 + 0.55 * t),
            )
        ).astype(np.float32)
    else:
        colors = np.tile(np.array(base, dtype=np.float32), (len(xyz), 1))
    return {
        "name": path.name,
        "layer": layer,
        "count_total": int(n),
        "count": int(len(xyz)),
        "center": [float(x.mean()), float(y.mean()), float(z.mean())],
        "origin": [ox, oy, oz],
        "bounds": {
            "min": [float(xyz[:, 0].min()), float(xyz[:, 1].min()), float(xyz[:, 2].min())],
            "max": [float(xyz[:, 0].max()), float(xyz[:, 1].max()), float(xyz[:, 2].max())],
        },
        "xyz": xyz,
        "colors": colors,
    }

def build_viewer_html(
    clouds: list[dict],
    *,
    title: str = "CrackInspect LiDAR",
) -> str:
    payloads = []
    for cloud in clouds:
        payloads.append(
            {
                "name": cloud["name"],
                "layer": cloud["layer"],
                "count": cloud["count"],
                "count_total": cloud["count_total"],
                "center": cloud["center"],
                "xyz": cloud["xyz"].reshape(-1).tolist(),
                "colors": cloud["colors"].reshape(-1).tolist(),
            }
        )
    data_json = json.dumps(payloads, separators=(",", ":"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    html, body {{ margin: 0; height: 100%; background: #07101c; color: #e8eef8; font-family: Segoe UI, sans-serif; overflow: hidden; }}
    #hud h1 {{ margin: 0 0 6px; font-size: 16px; }}
    #hud p, #hud li {{ margin: 0; font-size: 12px; color: #b7c4d8; line-height: 1.45; }}
    #hud ul {{ margin: 8px 0 0; padding-left: 0; list-style: none; display: grid; gap: 4px; }}
    #hud label {{ display: flex; gap: 8px; align-items: center; cursor: pointer; }}
    #hud input {{ margin: 0; }}
    #controls {{ position: absolute; right: 16px; bottom: 16px; z-index: 2; display: flex; gap: 8px; }}
    #controls button:hover {{ border-color: #73d9ff; }}
    #legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
    #legend i {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
    canvas {{ display: block; }}
  </style>
</head>
<body>
  <div id="hud">
    <div class="eyebrow">Site 223582 · real LAS points</div>
    <h1>{title}</h1>
    <p>Drag to orbit · scroll to zoom · right-drag to pan · click layer to toggle</p>
    <ul id="layers"></ul>
  </div>
  <div id="legend">
    <span><i style="background:#38b764"></i>Tree</span>
    <span><i style="background:#f3d65a"></i>Wires</span>
    <span><i style="background:#f2a900"></i>Powerline</span>
  </div>
  <div id="controls">
    <button type="button" id="btn-reset">Reset view</button>
    <button type="button" id="btn-top">Top view</button>
    <button type="button" id="btn-toggle">Hide layers</button>
  </div>
  <script type="importmap">
  {{
    "imports": {{
      "three": "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.module.min.js"
    }}
  }}
  </script>
  <script type="module">
    import * as THREE from "three";

    const clouds = {data_json};
    const layersEl = document.getElementById("layers");

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07101c);
    const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.1, 20000);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(innerWidth, innerHeight);
    document.body.appendChild(renderer.domElement);

    const root = new THREE.Group();
    scene.add(root);
    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const pointLayers = [];
    const layerChecks = [];

    let minX = Infinity, minY = Infinity, minZ = Infinity;
    let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
    for (const cloud of clouds) {{
      const positions = new Float32Array(cloud.xyz);
      const colors = new Float32Array(cloud.colors);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
      geo.computeBoundingBox();
      const bb = geo.boundingBox;
      minX = Math.min(minX, bb.min.x); minY = Math.min(minY, bb.min.y); minZ = Math.min(minZ, bb.min.z);
      maxX = Math.max(maxX, bb.max.x); maxY = Math.max(maxY, bb.max.y); maxZ = Math.max(maxZ, bb.max.z);
      const mat = new THREE.PointsMaterial({{ size: 0.18, vertexColors: true, sizeAttenuation: true }});
      const points = new THREE.Points(geo, mat);
      points.name = cloud.name;
      root.add(points);
      pointLayers.push(points);
      const li = document.createElement("li");
      const label = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = true;
      cb.addEventListener("change", () => {{ points.visible = cb.checked; }});
      label.appendChild(cb);
      label.appendChild(document.createTextNode(
        `${{cloud.name}} · ${{cloud.count.toLocaleString()}} / ${{cloud.count_total.toLocaleString()}} pts`
      ));
      li.appendChild(label);
      layersEl.appendChild(li);
      layerChecks.push(cb);
    }}

    const span = Math.max(20, maxX - minX, maxY - minY, maxZ - minZ);
    const mid = new THREE.Vector3((minX + maxX) * 0.5, (minY + maxY) * 0.5, (minZ + maxZ) * 0.5);

    let yaw = 0.8, pitch = 0.55, dist = span * 1.2;
    const home = {{ yaw: 0.8, pitch: 0.55, dist: span * 1.2, tx: mid.x, ty: mid.y, tz: mid.z }};
    let panning = false, rotating = false;
    let lastX = 0, lastY = 0;
    const target = mid.clone();
    const up = new THREE.Vector3(0, 0, 1); // Z-up for geospatial LAS

    function placeCamera() {{
      const cp = Math.cos(pitch), sp = Math.sin(pitch);
      const cy = Math.cos(yaw), sy = Math.sin(yaw);
      camera.up.copy(up);
      camera.position.set(
        target.x + dist * cp * cy,
        target.y + dist * cp * sy,
        target.z + dist * sp
      );
      camera.lookAt(target);
    }}
    placeCamera();

    document.getElementById("btn-reset").addEventListener("click", () => {{
      yaw = home.yaw; pitch = home.pitch; dist = home.dist;
      target.set(home.tx, home.ty, home.tz);
      placeCamera();
    }});
    document.getElementById("btn-top").addEventListener("click", () => {{
      yaw = 0; pitch = 1.2; dist = span * 1.35;
      target.copy(mid);
      placeCamera();
    }});
    let layersOn = true;
    document.getElementById("btn-toggle").addEventListener("click", (ev) => {{
      layersOn = !layersOn;
      for (let i = 0; i < pointLayers.length; i++) {{
        pointLayers[i].visible = layersOn;
        layerChecks[i].checked = layersOn;
      }}
      ev.target.textContent = layersOn ? "Hide layers" : "Show layers";
    }});

    renderer.domElement.addEventListener("contextmenu", (e) => e.preventDefault());
    renderer.domElement.addEventListener("pointerdown", (e) => {{
      lastX = e.clientX; lastY = e.clientY;
      if (e.button === 2) panning = true; else rotating = true;
    }});
    window.addEventListener("pointerup", () => {{ panning = false; rotating = false; }});
    window.addEventListener("pointermove", (e) => {{
      const dx = e.clientX - lastX, dy = e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      if (rotating) {{
        yaw -= dx * 0.005;
        pitch = Math.max(-1.2, Math.min(1.2, pitch + dy * 0.005));
        placeCamera();
      }} else if (panning) {{
        const panScale = dist * 0.0015;
        const right = new THREE.Vector3().crossVectors(camera.getWorldDirection(new THREE.Vector3()), up).normalize();
        const lift = up.clone();
        target.addScaledVector(right, -dx * panScale);
        target.addScaledVector(lift, dy * panScale);
        placeCamera();
      }}
    }});
    renderer.domElement.addEventListener("wheel", (e) => {{
      dist = Math.max(span * 0.08, Math.min(span * 10, dist * (e.deltaY > 0 ? 1.08 : 0.92)));
      placeCamera();
    }}, {{ passive: true }});

    window.addEventListener("resize", () => {{
      camera.aspect = innerWidth / innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(innerWidth, innerHeight);
    }});

    function tick() {{
      renderer.render(scene, camera);
      requestAnimationFrame(tick);
    }}
    tick();
  </script>
</body>
</html>
"""

def build_voxel_html(
    clouds: list[dict],
    *,
    title: str = "Corridor Site 223582",
    voxel_size: float = 0.55,
) -> str:
    payloads = []
    for cloud in clouds:
        xyz = cloud["xyz"]
        n = len(xyz)
        step = max(1, n // 3500) if n > 3500 else 1
        xyz = xyz[::step]
        payloads.append(
            {
                "name": cloud["name"],
                "layer": cloud["layer"],
                "count": int(len(xyz)),
                "count_total": cloud["count_total"],
                "xyz": xyz.reshape(-1).tolist(),
            }
        )
    data_json = json.dumps(payloads, separators=(",", ":"))
    layer_color = {
        "tree": 0x38B764,
        "wires": 0xF3D65A,
        "powerline": 0xFF7A26,
        "default": 0x7EB6D9,
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<style>
  html,body{{margin:0;height:100%;background:#07101c;color:#d8f3ff;font-family:Segoe UI,sans-serif;overflow:hidden}}
  canvas{{display:block}}
  .hud{{position:fixed;left:16px;top:16px;z-index:2;padding:12px 14px;max-width:340px;background:rgba(8,18,30,.82);border:1px solid rgba(123,190,224,.2);border-radius:10px}}
  .hud h1{{margin:0 0 4px;font-size:15px;letter-spacing:.04em;text-transform:uppercase}}
  .hud p,.hud li{{margin:0;font-size:11px;color:#8eb4c5;line-height:1.45}}
  .hud ul{{margin:8px 0 0;padding:0;list-style:none;display:grid;gap:4px}}
  .hud label{{display:flex;gap:8px;align-items:center;cursor:pointer;color:#cfe6f5}}
  .legend{{position:fixed;right:16px;bottom:16px;z-index:2;display:flex;gap:10px;flex-wrap:wrap;padding:8px 10px;background:rgba(8,18,30,.75);border:1px solid rgba(123,190,224,.18);border-radius:8px;font-size:11px}}
  .legend i{{width:10px;height:10px;border-radius:2px;display:inline-block;margin-right:5px}}
  .hint{{position:fixed;left:16px;bottom:16px;z-index:2;font-size:10px;color:#6f8fa4}}
</style>
</head>
<body>
<div class="hud">
  <h1>{title}</h1>
  <p>Real LAS → voxel blocks · Qwen-style presentation<br>Drag orbit · wheel zoom · right-drag pan</p>
  <ul id="layers"></ul>
</div>
<div class="legend">
  <span><i style="background:#38b764"></i>Tree</span>
  <span><i style="background:#f3d65a"></i>Wires</span>
  <span><i style="background:#ff7a26"></i>Powerline</span>
</div>
<div class="hint">Built from measured points (not hallucinated coords)</div>
<script type="module">
import * as THREE from "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.160.0/three.module.min.js";
const clouds = {data_json};
const LAYER_COLOR = {json.dumps(layer_color)};
const VOXEL = {voxel_size};

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x07101c);
const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, 0.1, 5000);
const renderer = new THREE.WebGLRenderer({{antialias:true}});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff, 0.85));
const sun = new THREE.DirectionalLight(0xfff1d2, 1.1);
sun.position.set(-40, 60, 80);
scene.add(sun);

const root = new THREE.Group();
scene.add(root);
const layerMeshes = [];
const checks = [];
let minX=Infinity,minY=Infinity,minZ=Infinity,maxX=-Infinity,maxY=-Infinity,maxZ=-Infinity;
const layersEl = document.getElementById("layers");

for (const cloud of clouds) {{
  const xyz = new Float32Array(cloud.xyz);
  const n = xyz.length / 3;
  const geo = new THREE.BoxGeometry(VOXEL, VOXEL, VOXEL);
  const color = LAYER_COLOR[cloud.layer] || LAYER_COLOR.default;
  const mat = new THREE.MeshStandardMaterial({{color, roughness:0.85, metalness:0.05}});
  const mesh = new THREE.InstancedMesh(geo, mat, n);
  const dummy = new THREE.Object3D();
  for (let i = 0; i < n; i++) {{
    const x = xyz[i*3], y = xyz[i*3+1], z = xyz[i*3+2];
    dummy.position.set(x, y, z);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
    minX=Math.min(minX,x); minY=Math.min(minY,y); minZ=Math.min(minZ,z);
    maxX=Math.max(maxX,x); maxY=Math.max(maxY,y); maxZ=Math.max(maxZ,z);
  }}
  mesh.instanceMatrix.needsUpdate = true;
  mesh.name = cloud.name;
  root.add(mesh);
  layerMeshes.push(mesh);
  const li = document.createElement("li");
  const label = document.createElement("label");
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.checked = true;
  cb.addEventListener("change", () => {{ mesh.visible = cb.checked; }});
  label.appendChild(cb);
  label.appendChild(document.createTextNode(`${{cloud.name}} · ${{cloud.count.toLocaleString()}} voxels / ${{cloud.count_total.toLocaleString()}} pts`));
  li.appendChild(label); layersEl.appendChild(li); checks.push(cb);
}}

const span = Math.max(20, maxX-minX, maxY-minY, maxZ-minZ);
const mid = new THREE.Vector3((minX+maxX)/2,(minY+maxY)/2,(minZ+maxZ)/2);
let yaw=0.85, pitch=0.55, dist=span*1.35;
const target = mid.clone();
const up = new THREE.Vector3(0,0,1);
function placeCamera() {{
  const cp=Math.cos(pitch), sp=Math.sin(pitch), cy=Math.cos(yaw), sy=Math.sin(yaw);
  camera.up.copy(up);
  camera.position.set(target.x+dist*cp*cy, target.y+dist*cp*sy, target.z+dist*sp);
  camera.lookAt(target);
}}
placeCamera();

let panning=false, rotating=false, lastX=0, lastY=0;
renderer.domElement.addEventListener("contextmenu", e => e.preventDefault());
renderer.domElement.addEventListener("pointerdown", e => {{
  lastX=e.clientX; lastY=e.clientY;
  if (e.button===2) panning=true; else rotating=true;
}});
window.addEventListener("pointerup", () => {{ panning=false; rotating=false; }});
window.addEventListener("pointermove", e => {{
  const dx=e.clientX-lastX, dy=e.clientY-lastY; lastX=e.clientX; lastY=e.clientY;
  if (rotating) {{
    yaw -= dx*0.005;
    pitch = Math.max(-1.2, Math.min(1.2, pitch+dy*0.005));
    placeCamera();
  }} else if (panning) {{
    const s = dist*0.0015;
    const right = new THREE.Vector3().crossVectors(camera.getWorldDirection(new THREE.Vector3()), up).normalize();
    target.addScaledVector(right, -dx*s);
    target.addScaledVector(up, dy*s);
    placeCamera();
  }}
}});
renderer.domElement.addEventListener("wheel", e => {{
  dist = Math.max(span*0.08, Math.min(span*10, dist*(e.deltaY>0?1.08:0.92)));
  placeCamera();
}}, {{passive:true}});
window.addEventListener("resize", () => {{
  camera.aspect = innerWidth/innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
}});
(function tick(){{ renderer.render(scene, camera); requestAnimationFrame(tick); }})();
</script>
</body>
</html>
"""

def build_voxel_viewer(
    names: list[str] | None = None,
    *,
    max_points: int = 60_000,
    out_name: str = "qwen3d_223582_voxel",
    voxel_size: float = 0.55,
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
    per = max(2_000, max_points // max(1, len(paths)))
    clouds = [load_points(p, max_points=per, origin=origin) for p in paths]
    LIDAR_SCENE_DIR.mkdir(parents=True, exist_ok=True)
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in out_name)[:80]
    out = LIDAR_SCENE_DIR / f"{stem}.html"
    title = "Corridor Site 223582 · LAS voxels"
    out.write_text(build_voxel_html(clouds, title=title, voxel_size=voxel_size), encoding="utf-8")
    meta = {
        "html": str(out),
        "html_name": out.name,
        "origin": list(origin),
        "mode": "voxel-from-las",
        "layers": [
            {"name": c["name"], "layer": c["layer"], "count": c["count"], "count_total": c["count_total"]}
            for c in clouds
        ],
        "bytes": out.stat().st_size,
        "view_url": f"/lidar/view/{out.name}",
        "note": "Voxels from real LAS coordinates. Qwen often invents fake coords from point counts.",
    }
    (LIDAR_SCENE_DIR / f"{stem}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta

def build_las_viewer(
    names: list[str] | None = None,
    *,
    max_points: int = 200_000,
    out_name: str | None = None,
) -> dict:
    root = LIDAR_DATA_ROOT
    if not root.is_dir():
        raise FileNotFoundError(f"LiDAR data root missing: {root}")
    if names:
        paths = [root / Path(n).name for n in names]
    else:
        paths = sorted(root.glob("*.las"))
        # like *22358* are not stacked on the same corridor by default.
        key = root.name
        matched = [p for p in paths if key in p.stem]
        if matched:
            paths = matched
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing LAS: " + ", ".join(missing))
    centers = np.array([_file_center(p) for p in paths], dtype=np.float64)
    origin = tuple(float(v) for v in centers.mean(axis=0))
    per = max(5_000, max_points // max(1, len(paths)))
    clouds = [load_points(p, max_points=per, origin=origin) for p in paths]
    LIDAR_SCENE_DIR.mkdir(parents=True, exist_ok=True)
    stem = out_name or ("scene_" + "_".join(Path(p).stem for p in paths[:3]))
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)[:80]
    out = LIDAR_SCENE_DIR / f"{stem}.html"
    title = "CrackInspect LiDAR · " + ", ".join(c["name"] for c in clouds)
    out.write_text(build_viewer_html(clouds, title=title), encoding="utf-8")
    meta = {
        "html": str(out),
        "html_name": out.name,
        "origin": list(origin),
        "layers": [
            {
                "name": c["name"],
                "layer": c["layer"],
                "count": c["count"],
                "count_total": c["count_total"],
                "center": c["center"],
                "bounds": c["bounds"],
            }
            for c in clouds
        ],
        "bytes": out.stat().st_size,
        "view_url": f"/lidar/view/{out.name}",
    }
    (LIDAR_SCENE_DIR / f"{stem}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta
