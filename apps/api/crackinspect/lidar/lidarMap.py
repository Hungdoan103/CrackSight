from __future__ import annotations

import base64
import json
from pathlib import Path

import laspy
import numpy as np
from pyproj import Transformer

from ..core.config import LIDAR_MAP_CACHE, LIDAR_MAP_ROOT

DEFAULT_EPSG = 32752
CACHE_VERSION = 4  # + intensity for CloudCompare-like greyscale

def list_map_las(root: Path | None = None) -> list[dict]:
    base = Path(root or LIDAR_MAP_ROOT)
    if not base.is_dir():
        return []
    out = []
    for path in sorted(base.glob("*.las")):
        with laspy.open(path) as reader:
            h = reader.header
            out.append(
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "points": int(h.point_count),
                    "mins": [float(v) for v in h.mins],
                    "maxs": [float(v) for v in h.maxs],
                }
            )
    return out

def _crs_epsg(header: laspy.LasHeader) -> int:
    try:
        crs = header.parse_crs()
        epsg = crs.to_epsg() if crs is not None else None
        if epsg:
            return int(epsg)
    except Exception:
        pass
    return DEFAULT_EPSG

def _sample_file(
    path: Path,
    *,
    max_points: int,
    transformer: Transformer,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    empty = (
        np.zeros(0, dtype=np.float64),
        np.zeros(0, dtype=np.float64),
        np.zeros(0, dtype=np.float64),
        np.zeros(0, dtype=np.float32),
    )
    with laspy.open(path) as reader:
        n = int(reader.header.point_count)
        if n <= 0 or max_points <= 0:
            return empty
        take = min(max_points, n)
        step = max(1, n // take)
        xs: list[np.ndarray] = []
        ys: list[np.ndarray] = []
        zs: list[np.ndarray] = []
        ints: list[np.ndarray] = []
        kept = 0
        for chunk in reader.chunk_iterator(1_000_000):
            cx = np.asarray(chunk.x, dtype=np.float64)
            cy = np.asarray(chunk.y, dtype=np.float64)
            cz = np.asarray(chunk.z, dtype=np.float64)
            if "intensity" in chunk.point_format.dimension_names:
                ci = np.asarray(chunk.intensity, dtype=np.float32)
            else:
                ci = np.zeros(len(cx), dtype=np.float32)
            m = len(cx)
            if m == 0:
                continue
            start = int(rng.integers(0, min(step, m)))
            idx = np.arange(start, m, step, dtype=np.int64)
            if kept + len(idx) > take:
                idx = idx[: take - kept]
            if len(idx) == 0:
                continue
            xs.append(cx[idx])
            ys.append(cy[idx])
            zs.append(cz[idx])
            ints.append(ci[idx])
            kept += len(idx)
            if kept >= take:
                break
    if not xs:
        return empty
    x = np.concatenate(xs)[:take]
    y = np.concatenate(ys)[:take]
    z = np.concatenate(zs)[:take]
    intensity = np.concatenate(ints)[:take]
    lon, lat = transformer.transform(x, y)
    return (
        np.asarray(lon, dtype=np.float64),
        np.asarray(lat, dtype=np.float64),
        z.astype(np.float64),
        intensity.astype(np.float32),
    )

def _b64_f32(arr: np.ndarray) -> str:
    return base64.b64encode(np.asarray(arr, dtype=np.float32).tobytes()).decode("ascii")

def build_overlay(
    *,
    max_points: int = 2_000_000,
    force: bool = False,
    root: Path | None = None,
) -> dict:
    cache = Path(LIDAR_MAP_CACHE)
    max_points = int(max(2_000, min(max_points, 2_000_000)))
    if cache.is_file() and not force:
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            if (
                int(data.get("version", 0)) == CACHE_VERSION
                and data.get("format") == "lidar-3d"
                and int(data.get("max_points_request", 0)) >= max_points
                and data.get("xyz_b64")
                and data.get("intensity_b64")
            ):
                return data
        except Exception:
            pass

    base = Path(root or LIDAR_MAP_ROOT)
    if not base.is_dir():
        raise FileNotFoundError(f"LiDAR map folder missing: {base}")
    files = sorted(base.glob("*.las"))
    if not files:
        raise FileNotFoundError(f"No .las under {base}")

    with laspy.open(files[0]) as reader:
        epsg = _crs_epsg(reader.header)
    transformer = Transformer.from_crs(epsg, 4326, always_xy=True)

    per = max(500, max_points // len(files))
    lons: list[np.ndarray] = []
    lats: list[np.ndarray] = []
    zs: list[np.ndarray] = []
    ints: list[np.ndarray] = []
    file_stats = []
    for i, path in enumerate(files):
        lon, lat, z, intensity = _sample_file(
            path, max_points=per, transformer=transformer, seed=i + 7
        )
        if len(lon) == 0:
            continue
        lons.append(lon)
        lats.append(lat)
        zs.append(z)
        ints.append(intensity)
        file_stats.append({"name": path.name, "sampled": int(len(lon))})

    if not lons:
        raise RuntimeError("No points sampled from LAS files")

    lon = np.concatenate(lons)
    lat = np.concatenate(lats)
    z = np.concatenate(zs)
    intensity = np.concatenate(ints)
    if len(lon) > max_points:
        rng = np.random.default_rng(0)
        pick = rng.choice(len(lon), size=max_points, replace=False)
        lon, lat, z, intensity = lon[pick], lat[pick], z[pick], intensity[pick]

    z0, z1 = float(np.percentile(z, 2)), float(np.percentile(z, 98))
    i0, i1 = float(np.percentile(intensity, 2)), float(np.percentile(intensity, 98))
    xyz = np.column_stack((lon, lat, z)).astype(np.float32)

    payload = {
        "version": CACHE_VERSION,
        "format": "lidar-3d",
        "color_default": "intensity",
        "note": "LAS RGB is empty (0); CloudCompare-like view uses Intensity greyscale.",
        "crs": f"EPSG:{epsg}→EPSG:4326",
        "source_root": str(base),
        "max_points_request": max_points,
        "count": int(len(xyz)),
        "files": file_stats,
        "bounds": {
            "west": float(lon.min()),
            "south": float(lat.min()),
            "east": float(lon.max()),
            "north": float(lat.max()),
            "zmin": float(z.min()),
            "zmax": float(z.max()),
        },
        "z_stretch": {"lo": z0, "hi": z1},
        "intensity_stretch": {"lo": i0, "hi": i1},
        "xyz_b64": _b64_f32(xyz.reshape(-1)),
        "intensity_b64": _b64_f32(intensity),
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload
